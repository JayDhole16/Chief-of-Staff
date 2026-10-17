"""
Meeting slot computation service.
Implements T05.5 per BACKEND_SCHEMA §6.3, §7.8 and TRD §11.6.
Pure logic: server-computed meeting availability, busy block avoidance, buffer margins,
timezone projections, signed slot token minting and validation, and busy cache staleness rejection.
"""

from dataclasses import dataclass
from datetime import datetime, time as dtime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from backend.security.tokens import Slot, mint_slot_token, verify_slot_token


class CalendarDataStaleError(Exception):
    """Raised when calendar busy cache is older than 15 minutes."""
    pass


class DateOutOfRangeError(Exception):
    """Raised when requested date is outside allowed calendar days horizon."""
    pass


class BookingNotAllowedError(Exception):
    """Raised when task kind or mandate prohibits meeting booking."""
    pass


@dataclass(frozen=True)
class BusyInterval:
    """An existing busy block or hold."""
    start_utc: datetime
    end_utc: datetime


@dataclass(frozen=True)
class FindSlotsInput:
    """Input parameters for finding slots."""
    task_id: str
    target_date: str  # YYYY-MM-DD
    part_of_day: Literal["morning", "afternoon", "evening", "any"]
    duration_minutes: Literal[30, 45, 60]
    tz_perspective: Literal["founder", "contact"]
    founder_tz: str
    contact_tz: str
    calendar_days: list[str]  # List of allowed YYYY-MM-DD strings (horizon)
    busy_intervals: list[BusyInterval]  # Existing busy blocks in UTC
    calendar_busy_synced_at: datetime  # When busy cache was last refreshed
    now_utc: datetime  # Current time for freshness and min_notice checks
    slot_signing_key: str
    min_notice_minutes: int = 120  # Minimum 2 hours notice
    meeting_buffer_minutes: int = 15  # Buffer before and after meetings
    slot_grid_minutes: int = 30  # Align to 30-minute grid
    max_slots: int = 4  # Return at most 4 slots S1..S4


@dataclass(frozen=True)
class FindSlotsResult:
    """Result of slot search."""
    date: str
    window_display: str
    availability_as_of: str
    slots: list[Slot]
    note: str | None = None


class SlotService:
    """Service for computing available calendar slots."""

    @staticmethod
    def find_slots(params: FindSlotsInput) -> FindSlotsResult:
        """
        Compute available slots according to TRD §11.6 algorithm:
          1. Check calendar busy cache freshness: older than 15 min -> CalendarDataStaleError.
          2. Validate target_date in calendar_days.
          3. Determine part_of_day window in perspective zone.
          4. Convert window to UTC and intersect with founder working hours (09:30-18:30 Mon-Fri).
          5. Generate candidate slots aligned to slot_grid_minutes.
          6. Remove candidates overlapping busy blocks or holds (expanded by meeting_buffer_minutes on both sides).
          7. Remove candidates starting earlier than now + min_notice_minutes.
          8. Format displays in founder and contact zones.
          9. Return up to max_slots (S1..S4) with signed slot tokens.
        """
        if params.slot_grid_minutes <= 0:
            raise ValueError("slot_grid_minutes must be positive")
        if params.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")

        # 1. Busy cache freshness check (15 minutes = 900 seconds)
        cache_age_seconds = (params.now_utc - params.calendar_busy_synced_at).total_seconds()
        if cache_age_seconds > 900:
            raise CalendarDataStaleError(
                f"Calendar busy cache is stale ({int(cache_age_seconds)}s old, limit is 900s)"
            )

        # 2. Date in calendar days
        if params.target_date not in params.calendar_days:
            raise DateOutOfRangeError(
                f"Date {params.target_date} is not within active calendar horizon"
            )

        f_tz = ZoneInfo(params.founder_tz)
        c_tz = ZoneInfo(params.contact_tz)
        perspective_tz = f_tz if params.tz_perspective == "founder" else c_tz

        # 3. Part-of-day window in perspective zone
        year, month, day = map(int, params.target_date.split("-"))

        if params.part_of_day == "morning":
            win_start_time = dtime(9, 0)
            win_end_time = dtime(12, 0)
            win_name = "Morning"
        elif params.part_of_day == "afternoon":
            win_start_time = dtime(13, 0)
            win_end_time = dtime(17, 0)
            win_name = "Afternoon"
        elif params.part_of_day == "evening":
            win_start_time = dtime(17, 0)
            win_end_time = dtime(19, 0)
            win_name = "Evening"
        else:
            win_start_time = dtime(9, 30)
            win_end_time = dtime(18, 30)
            win_name = "Working Hours"

        local_win_start = datetime(year, month, day, win_start_time.hour, win_start_time.minute, tzinfo=perspective_tz)
        local_win_end = datetime(year, month, day, win_end_time.hour, win_end_time.minute, tzinfo=perspective_tz)

        # Founder working hours for that date in founder local time (09:30 - 18:30 Mon-Fri)
        founder_local_date = local_win_start.astimezone(f_tz).date()
        if founder_local_date.weekday() >= 5:  # Saturday or Sunday
            return FindSlotsResult(
                date=params.target_date,
                window_display=f"{win_name} ({params.target_date})",
                availability_as_of=params.now_utc.isoformat(),
                slots=[],
                note="Founder does not work on weekends",
            )

        founder_work_start = datetime(
            founder_local_date.year, founder_local_date.month, founder_local_date.day,
            9, 30, tzinfo=f_tz
        )
        founder_work_end = datetime(
            founder_local_date.year, founder_local_date.month, founder_local_date.day,
            18, 30, tzinfo=f_tz
        )

        # Intersect windows in UTC
        win_start_utc = max(local_win_start.astimezone(ZoneInfo("UTC")), founder_work_start.astimezone(ZoneInfo("UTC")))
        win_end_utc = min(local_win_end.astimezone(ZoneInfo("UTC")), founder_work_end.astimezone(ZoneInfo("UTC")))

        if win_start_utc >= win_end_utc:
            return FindSlotsResult(
                date=params.target_date,
                window_display=f"{win_name} ({params.target_date})",
                availability_as_of=params.now_utc.isoformat(),
                slots=[],
                note="No overlapping working hours in selected window",
            )

        duration = timedelta(minutes=params.duration_minutes)
        buffer = timedelta(minutes=params.meeting_buffer_minutes)
        min_notice = timedelta(minutes=params.min_notice_minutes)
        grid = timedelta(minutes=params.slot_grid_minutes)

        # 4. Generate candidate slot starts aligned forward to slot_grid_minutes in founder zone
        founder_start = win_start_utc.astimezone(f_tz)
        minute_offset = founder_start.minute % params.slot_grid_minutes
        has_subminute = founder_start.second > 0 or founder_start.microsecond > 0
        if minute_offset != 0 or has_subminute:
            advance_minutes = params.slot_grid_minutes - minute_offset
            founder_start = founder_start.replace(second=0, microsecond=0) + timedelta(minutes=advance_minutes)
        else:
            founder_start = founder_start.replace(second=0, microsecond=0)

        current_candidate_start_utc = founder_start.astimezone(ZoneInfo("UTC"))
        valid_slots: list[Slot] = []
        slot_index = 1

        while current_candidate_start_utc + duration <= win_end_utc and len(valid_slots) < params.max_slots:
            cand_start = current_candidate_start_utc
            cand_end = cand_start + duration

            # Check min notice
            if cand_start < params.now_utc + min_notice:
                current_candidate_start_utc += grid
                continue

            # Check busy overlap with buffer: [busy.start - buffer, busy.end + buffer]
            overlap = False
            for busy in params.busy_intervals:
                buffered_busy_start = busy.start_utc - buffer
                buffered_busy_end = busy.end_utc + buffer

                if cand_start < buffered_busy_end and cand_end > buffered_busy_start:
                    overlap = True
                    break

            if not overlap:
                label = f"S{slot_index}"
                slot_id = mint_slot_token(
                    task_id=params.task_id,
                    start=cand_start,
                    end=cand_end,
                    signing_key=params.slot_signing_key,
                )

                cand_f_start = cand_start.astimezone(f_tz)
                cand_f_end = cand_end.astimezone(f_tz)
                f_tz_abbr = "IST" if params.founder_tz == "Asia/Kolkata" else (cand_f_start.strftime("%Z") or params.founder_tz)
                display_founder = (
                    f"{cand_f_start.strftime('%a %d %b')}, "
                    f"{cand_f_start.strftime('%I:%M').lstrip('0')}-"
                    f"{cand_f_end.strftime('%I:%M').lstrip('0')} {cand_f_end.strftime('%p')} {f_tz_abbr}"
                )

                display_contact = None
                if params.contact_tz != params.founder_tz:
                    cand_c_start = cand_start.astimezone(c_tz)
                    cand_c_end = cand_end.astimezone(c_tz)
                    tz_name = "IST" if params.contact_tz == "Asia/Kolkata" else (cand_c_start.strftime("%Z") or params.contact_tz)
                    display_contact = (
                        f"{cand_c_start.strftime('%a %d %b')}, "
                        f"{cand_c_start.strftime('%I:%M').lstrip('0')}-"
                        f"{cand_c_end.strftime('%I:%M').lstrip('0')} {cand_c_end.strftime('%p')} {tz_name}"
                    )

                valid_slots.append(
                    Slot(
                        label=label,
                        slot_id=slot_id,
                        start=cand_start,
                        end=cand_end,
                        display_founder=display_founder,
                        display_contact=display_contact,
                    )
                )
                slot_index += 1

            current_candidate_start_utc += grid

        return FindSlotsResult(
            date=params.target_date,
            window_display=f"{win_name} ({params.target_date})",
            availability_as_of=params.now_utc.isoformat(),
            slots=valid_slots,
        )

    @staticmethod
    def verify_slot(slot_id: str, task_id: str, signing_key: str, now_epoch: int | None = None) -> dict:
        """Verify that a chosen slot token is authentic, scoped to this task, and unexpired."""
        return verify_slot_token(
            token=slot_id,
            expected_task_id=task_id,
            signing_key=signing_key,
            now_epoch=now_epoch,
        )
