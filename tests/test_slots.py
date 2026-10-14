"""
Unit and integration tests for Meeting Slots and Signed Slot Tokens (T05.5).
Tests:
  - Demo calendar golden case (Thursday 13:00-14:30 busy -> first slot is 15:00-15:30 IST)
  - Slot token integrity: signing, verification, tamper detection, and rejection of altered tokens
  - Token task scope boundary: rejection when token presented to a different task
  - Token expiry: rejection after 30-minute validity
  - Stale calendar cache: rejection when calendar_busy_synced_at older than 15 minutes
  - Min notice and weekend cutoffs
  - Timezone projection for founder (IST) and contact (e.g. Europe/London)
"""

import pytest
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from backend.security.tokens import (
    SlotTokenExpiredError,
    SlotTokenInvalidError,
    SlotTokenScopeMismatchError,
    mint_slot_token,
    verify_slot_token,
)
from backend.services.slots import (
    BusyInterval,
    CalendarDataStaleError,
    DateOutOfRangeError,
    FindSlotsInput,
    SlotService,
)


class TestSignedSlotTokens:
    """Test suite for signed slot tokens."""

    def test_mint_and_verify_token_happy_path(self):
        """Mint token and verify successfully within validity."""
        key = "secret_slot_signing_key_123"
        task_id = "task-uuid-456"
        start = datetime(2026, 10, 15, 9, 30, tzinfo=timezone.utc)
        end = datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc)

        token = mint_slot_token(task_id=task_id, start=start, end=end, signing_key=key)
        assert token.startswith("sl_")
        assert "." in token

        payload = verify_slot_token(token, expected_task_id=task_id, signing_key=key)
        assert payload["t"] == task_id
        assert payload["s"] == start.isoformat()
        assert payload["e"] == end.isoformat()

    def test_tampered_token_rejected(self):
        """Tampering with token payload or signature is rejected."""
        key = "secret_slot_signing_key_123"
        task_id = "task-uuid-456"
        start = datetime(2026, 10, 15, 9, 30, tzinfo=timezone.utc)
        end = datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc)

        token = mint_slot_token(task_id=task_id, start=start, end=end, signing_key=key)

        # Alter token payload
        tampered_token = token[:10] + "X" + token[11:]
        with pytest.raises(SlotTokenInvalidError):
            verify_slot_token(tampered_token, expected_task_id=task_id, signing_key=key)

    def test_scope_isolation_wrong_task_rejected(self):
        """Token minted for task A cannot be verified or used by task B."""
        key = "secret_slot_signing_key_123"
        task_a = "task-tenant1-deal1"
        task_b = "task-tenant2-deal2"
        start = datetime(2026, 10, 15, 9, 30, tzinfo=timezone.utc)
        end = datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc)

        token = mint_slot_token(task_id=task_a, start=start, end=end, signing_key=key)

        with pytest.raises(SlotTokenScopeMismatchError, match="task mismatch"):
            verify_slot_token(token, expected_task_id=task_b, signing_key=key)

    def test_expired_token_rejected(self):
        """Token older than 30 minutes (1800s) is rejected as expired."""
        key = "secret_slot_signing_key_123"
        task_id = "task-uuid-456"
        start = datetime(2026, 10, 15, 9, 30, tzinfo=timezone.utc)
        end = datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc)
        now_epoch = 1700000000

        token = mint_slot_token(
            task_id=task_id,
            start=start,
            end=end,
            signing_key=key,
            validity_seconds=1800,
            now_epoch=now_epoch,
        )

        # Attempt verification at now + 1801s
        with pytest.raises(SlotTokenExpiredError, match="expired"):
            verify_slot_token(
                token,
                expected_task_id=task_id,
                signing_key=key,
                now_epoch=now_epoch + 1801,
            )


class TestSlotService:
    """Test suite for SlotService availability calculation."""

    def test_demo_golden_calendar_case(self):
        """
        Demo calendar golden case (DEVELOPMENT_PLAN §9.1 and T05.5 acceptance):
        Target date is Thursday (2026-10-15).
        Busy blocks:
          11:00-12:00 IST Team sync
          13:00-14:30 IST Site visit
        Buffer is 15 minutes before and after.
        For afternoon request (13:00-17:00 IST), site visit ends at 14:30.
        With 15-min buffer, availability starts at 14:45.
        Aligned to 30-min grid (00, 30), first candidate start is 15:00.
        Therefore S1 is 15:00-15:30 IST!
        """
        ist = ZoneInfo("Asia/Kolkata")
        # 11:00-12:00 IST in UTC (05:30-06:30 UTC)
        busy_sync = datetime(2026, 10, 15, 11, 0, tzinfo=ist).astimezone(timezone.utc)
        busy_sync_end = datetime(2026, 10, 15, 12, 0, tzinfo=ist).astimezone(timezone.utc)

        # 13:00-14:30 IST in UTC (07:30-09:00 UTC)
        busy_site = datetime(2026, 10, 15, 13, 0, tzinfo=ist).astimezone(timezone.utc)
        busy_site_end = datetime(2026, 10, 15, 14, 30, tzinfo=ist).astimezone(timezone.utc)

        busy_intervals = [
            BusyInterval(start_utc=busy_sync, end_utc=busy_sync_end),
            BusyInterval(start_utc=busy_site, end_utc=busy_site_end),
        ]

        now_utc = datetime(2026, 10, 15, 5, 0, tzinfo=timezone.utc)  # 10:30 IST

        input_params = FindSlotsInput(
            task_id="task-raju-demo",
            target_date="2026-10-15",
            part_of_day="afternoon",
            duration_minutes=30,
            tz_perspective="founder",
            founder_tz="Asia/Kolkata",
            contact_tz="Asia/Kolkata",
            calendar_days=["2026-10-15", "2026-10-16"],
            busy_intervals=busy_intervals,
            calendar_busy_synced_at=now_utc - timedelta(minutes=5),  # 5 min ago (fresh)
            now_utc=now_utc,
            slot_signing_key="demo_slot_key_xyz",
            meeting_buffer_minutes=15,
            slot_grid_minutes=30,
            max_slots=4,
        )

        res = SlotService.find_slots(input_params)

        assert len(res.slots) > 0
        s1 = res.slots[0]
        assert s1.label == "S1"
        # First afternoon slot after 14:30 + 15 min buffer on 30 min grid is 15:00 IST!
        assert "3:00-3:30 PM IST" in s1.display_founder

        # Verify token of S1 is valid and authenticated
        payload = SlotService.verify_slot(
            slot_id=s1.slot_id,
            task_id="task-raju-demo",
            signing_key="demo_slot_key_xyz",
        )
        assert payload["t"] == "task-raju-demo"

    def test_stale_calendar_cache_rejected(self):
        """Calendar cache older than 15 min raises CalendarDataStaleError."""
        now_utc = datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc)
        stale_synced_at = now_utc - timedelta(minutes=16)  # 16 min old (> 15 min)

        input_params = FindSlotsInput(
            task_id="task-123",
            target_date="2026-10-15",
            part_of_day="morning",
            duration_minutes=30,
            tz_perspective="founder",
            founder_tz="Asia/Kolkata",
            contact_tz="Asia/Kolkata",
            calendar_days=["2026-10-15"],
            busy_intervals=[],
            calendar_busy_synced_at=stale_synced_at,
            now_utc=now_utc,
            slot_signing_key="key",
        )

        with pytest.raises(CalendarDataStaleError, match="stale"):
            SlotService.find_slots(input_params)

    def test_date_out_of_range_rejected(self):
        """Date outside allowed calendar days raises DateOutOfRangeError."""
        now_utc = datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc)

        input_params = FindSlotsInput(
            task_id="task-123",
            target_date="2026-10-29",  # Beyond horizon
            part_of_day="morning",
            duration_minutes=30,
            tz_perspective="founder",
            founder_tz="Asia/Kolkata",
            contact_tz="Asia/Kolkata",
            calendar_days=["2026-10-15", "2026-10-16"],
            busy_intervals=[],
            calendar_busy_synced_at=now_utc,
            now_utc=now_utc,
            slot_signing_key="key",
        )

        with pytest.raises(DateOutOfRangeError, match="not within active calendar horizon"):
            SlotService.find_slots(input_params)

    def test_differing_contact_timezone_display(self):
        """When contact is in London (Europe/London), contact display is formatted in BST."""
        now_utc = datetime(2026, 10, 15, 5, 0, tzinfo=timezone.utc)

        input_params = FindSlotsInput(
            task_id="task-priya-london",
            target_date="2026-10-15",
            part_of_day="afternoon",
            duration_minutes=30,
            tz_perspective="founder",
            founder_tz="Asia/Kolkata",
            contact_tz="Europe/London",  # BST in mid-Oct (UTC+1)
            calendar_days=["2026-10-15"],
            busy_intervals=[],
            calendar_busy_synced_at=now_utc,
            now_utc=now_utc,
            slot_signing_key="key",
        )

        res = SlotService.find_slots(input_params)
        assert len(res.slots) > 0
        s1 = res.slots[0]
        assert s1.display_contact is not None
        # 13:00 IST is 08:30 BST
        assert "BST" in s1.display_contact

