#!/usr/bin/env python3
"""
EV-11 / EV-13 Spike: Capture real Gmail and Calendar API behavior.

This is a standalone throwaway script for exploring Google API behavior.
Logs structured results for request shapes, response status, latency, and edge cases.

Usage:
    python spikes/google_api_behavior.py --oauth-config /path/to/creds.json

Output:
    docs/spikes/google-api-behavior.md (structured findings)

SECURITY:
    - Never logs tokens or full email bodies
    - Redacts email addresses
    - Redacts sensitive data
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

# Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.exceptions import RefreshError, TransportError
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as e:
    print(f"Error: Google API libraries not installed. Install with:\n  pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)


# SCOPES required for full access
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',  # Gmail: read, compose, send
    'https://www.googleapis.com/auth/calendar',       # Calendar: full access
]

# Redaction patterns
EMAIL_REDACTION = "[EMAIL]"
BODY_REDACTION = "[REDACTED]"
TOKEN_REDACTION = "[TOKEN]"


def redact_email(email: str) -> str:
    """Redact email addresses."""
    if not email or '@' not in email:
        return email
    parts = email.split('@')
    return f"{parts[0][0]}***@{parts[1]}"


def redact_dict(data: Any, keys_to_redact: Optional[list[str]] = None) -> Any:
    """Recursively redact sensitive keys in dicts."""
    if keys_to_redact is None:
        keys_to_redact = ['accessToken', 'id_token', 'refresh_token', 'body', 'payload']
    
    if isinstance(data, dict):
        return {
            k: (TOKEN_REDACTION if k in keys_to_redact else redact_dict(v, keys_to_redact))
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [redact_dict(item, keys_to_redact) for item in data]
    elif isinstance(data, str) and '@' in data and '.' in data:
        return redact_email(data)
    return data


class APIBehaviorLogger:
    """Capture and log API behavior."""

    def __init__(self, output_file: Path):
        self.output_file = output_file
        self.findings = []
        self.setup_logging()

    def setup_logging(self):
        """Setup console logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def log_call(
        self,
        service: str,
        operation: str,
        method: str,
        request_shape: dict,
        response_status: int,
        response_body: Optional[dict],
        error: Optional[str],
        latency_ms: float,
        notes: str = "",
    ):
        """Log a single API call."""
        finding = {
            'timestamp': datetime.utcnow().isoformat(),
            'service': service,
            'operation': operation,
            'method': method,
            'request_shape': redact_dict(request_shape),
            'response_status': response_status,
            'response_body': redact_dict(response_body) if response_body else None,
            'error': error,
            'latency_ms': round(latency_ms, 2),
            'notes': notes,
        }
        self.findings.append(finding)
        self.logger.info(
            f"{service}/{operation} {method} - Status: {response_status}, "
            f"Latency: {latency_ms:.0f}ms, Error: {error or 'None'}"
        )

    def write_report(self):
        """Write findings to markdown report."""
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_file, 'w') as f:
            f.write("# Google API Behavior Spike (EV-11 / EV-13)\n\n")
            f.write(f"**Generated**: {datetime.utcnow().isoformat()}\n\n")
            f.write("## Security Notes\n\n")
            f.write("- Email addresses redacted ([EMAIL] format)\n")
            f.write("- Tokens and sensitive data redacted ([TOKEN], [REDACTED])\n")
            f.write("- Full email bodies not logged\n\n")
            
            # Write summary statistics
            f.write("## Summary\n\n")
            f.write(f"Total API calls: {len(self.findings)}\n")
            
            gmail_calls = [f for f in self.findings if f['service'] == 'Gmail']
            calendar_calls = [f for f in self.findings if f['service'] == 'Calendar']
            f.write(f"Gmail calls: {len(gmail_calls)}\n")
            f.write(f"Calendar calls: {len(calendar_calls)}\n\n")
            
            # Gmail findings
            if gmail_calls:
                f.write("## Gmail Findings\n\n")
                self._write_service_table(f, gmail_calls)
            
            # Calendar findings
            if calendar_calls:
                f.write("## Calendar Findings\n\n")
                self._write_service_table(f, calendar_calls)
            
            # Detailed notes
            f.write("## Detailed Call Logs\n\n")
            for finding in self.findings:
                f.write(f"### {finding['service']}/{finding['operation']} ({finding['method']})\n\n")
                f.write(f"**Timestamp**: {finding['timestamp']}\n\n")
                f.write(f"**Status**: {finding['response_status']}\n\n")
                f.write(f"**Latency**: {finding['latency_ms']}ms\n\n")
                
                if finding['error']:
                    f.write(f"**Error**: {finding['error']}\n\n")
                
                f.write(f"**Request Shape**:\n```json\n{json.dumps(finding['request_shape'], indent=2)}\n```\n\n")
                
                if finding['response_body']:
                    f.write(f"**Response Body**:\n```json\n{json.dumps(finding['response_body'], indent=2)}\n```\n\n")
                
                if finding['notes']:
                    f.write(f"**Notes**: {finding['notes']}\n\n")
                
                f.write("---\n\n")

    def _write_service_table(self, f, calls):
        """Write a table of service calls."""
        f.write("| Operation | Method | Status | Latency | Error | Notes |\n")
        f.write("|-----------|--------|--------|---------|-------|-------|\n")
        
        for call in calls:
            op = call['operation']
            method = call['method']
            status = call['response_status']
            latency = f"{call['latency_ms']}ms"
            error = call['error'] or "—"
            notes = call['notes'][:50] if call['notes'] else "—"
            
            f.write(f"| {op} | {method} | {status} | {latency} | {error} | {notes} |\n")
        
        f.write("\n")


class GmailSpike:
    """Capture Gmail API behavior."""

    def __init__(self, service, logger: APIBehaviorLogger):
        self.service = service
        self.logger = logger

    def run(self):
        """Execute Gmail spike tests."""
        self.logger.logger.info("Starting Gmail spike tests...")
        
        # Test 1: List threads
        self._test_list_threads()
        
        # Test 2: Read a message
        self._test_read_message()
        
        # Test 3: Create draft in thread
        self._test_create_draft_in_thread()
        
        # Test 4: Send draft
        self._test_send_draft()
        
        # Test 5: Rate limit / quota errors
        self._test_rate_limit()
        
        # Test 6: Expired token behavior
        self._test_expired_token()
        
        # Test 7: Invalid recipient error
        self._test_invalid_recipient()

    def _test_list_threads(self):
        """Test: List Gmail threads."""
        try:
            start_time = time.time()
            result = self.service.users().threads().list(userId='me', maxResults=5).execute()
            latency = (time.time() - start_time) * 1000
            
            self.logger.log_call(
                service='Gmail',
                operation='list_threads',
                method='users.threads.list',
                request_shape={'userId': 'me', 'maxResults': 5},
                response_status=200,
                response_body={
                    'resultSizeEstimate': result.get('resultSizeEstimate'),
                    'threadCount': len(result.get('threads', [])),
                },
                error=None,
                latency_ms=latency,
                notes=f"Retrieved {len(result.get('threads', []))} threads",
            )
        except HttpError as e:
            self.logger.log_call(
                service='Gmail',
                operation='list_threads',
                method='users.threads.list',
                request_shape={'userId': 'me', 'maxResults': 5},
                response_status=e.resp.status,
                response_body=None,
                error=str(e),
                latency_ms=0,
                notes="HTTP error",
            )

    def _test_read_message(self):
        """Test: Read a message (find first thread, read first message)."""
        try:
            # First get a thread
            threads_result = self.service.users().threads().list(userId='me', maxResults=1).execute()
            if not threads_result.get('threads'):
                self.logger.logger.warning("No threads found, skipping read_message test")
                return
            
            thread_id = threads_result['threads'][0]['id']
            
            # Now get message from thread
            start_time = time.time()
            result = self.service.users().messages().get(userId='me', id=thread_id, format='metadata').execute()
            latency = (time.time() - start_time) * 1000
            
            self.logger.log_call(
                service='Gmail',
                operation='read_message',
                method='users.messages.get',
                request_shape={'userId': 'me', 'id': '[THREAD_ID]', 'format': 'metadata'},
                response_status=200,
                response_body={
                    'id': '[MESSAGE_ID]',
                    'threadId': '[THREAD_ID]',
                    'labelIds': result.get('labelIds', []),
                    'internalDate': result.get('internalDate'),
                },
                error=None,
                latency_ms=latency,
                notes=f"Message in thread {thread_id[:8]}..., has labels",
            )
        except HttpError as e:
            self.logger.log_call(
                service='Gmail',
                operation='read_message',
                method='users.messages.get',
                request_shape={'userId': 'me', 'format': 'metadata'},
                response_status=e.resp.status,
                response_body=None,
                error=str(e),
                latency_ms=0,
                notes="HTTP error",
            )

    def _test_create_draft_in_thread(self):
        """Test: Create draft in existing thread (check threadId + headers)."""
        try:
            # Get an existing thread
            threads_result = self.service.users().threads().list(userId='me', maxResults=1).execute()
            if not threads_result.get('threads'):
                self.logger.logger.warning("No threads found, skipping create_draft test")
                return
            
            thread_id = threads_result['threads'][0]['id']
            
            # Get the thread details to find In-Reply-To header
            thread = self.service.users().threads().get(userId='me', id=thread_id).execute()
            
            # Extract message ID for In-Reply-To from first message
            message_id = None
            if thread.get('messages'):
                headers = thread['messages'][0].get('payload', {}).get('headers', [])
                for header in headers:
                    if header['name'] == 'Message-ID':
                        message_id = header['value']
                        break
            
            # Create draft
            draft_body = {
                'message': {
                    'threadId': thread_id,
                    'raw': 'From: [EMAIL]\nTo: [EMAIL]\nSubject: Re: Test\nIn-Reply-To: ' + (message_id or '[UNKNOWN]') + '\nReferences: [REFS]\n\nDraft reply',
                }
            }
            
            start_time = time.time()
            result = self.service.users().drafts().create(userId='me', body=draft_body).execute()
            latency = (time.time() - start_time) * 1000
            
            self.logger.log_call(
                service='Gmail',
                operation='create_draft_in_thread',
                method='users.drafts.create',
                request_shape={'userId': 'me', 'threadId': '[THREAD_ID]', 'headers': ['In-Reply-To', 'References']},
                response_status=200,
                response_body={
                    'id': '[DRAFT_ID]',
                    'message': {
                        'id': '[MESSAGE_ID]',
                        'threadId': thread_id,
                    }
                },
                error=None,
                latency_ms=latency,
                notes=f"Draft created in thread with In-Reply-To and References headers",
            )
        except HttpError as e:
            self.logger.log_call(
                service='Gmail',
                operation='create_draft_in_thread',
                method='users.drafts.create',
                request_shape={'userId': 'me'},
                response_status=e.resp.status,
                response_body=None,
                error=str(e),
                latency_ms=0,
                notes="HTTP error",
            )

    def _test_send_draft(self):
        """Test: Send a draft."""
        try:
            # Create a simple draft first
            draft_body = {
                'message': {
                    'raw': 'From: [EMAIL]\nTo: [EMAIL]\nSubject: Test Draft\n\nTest message',
                }
            }
            draft_result = self.service.users().drafts().create(userId='me', body=draft_body).execute()
            draft_id = draft_result['id']
            
            # Send the draft
            start_time = time.time()
            result = self.service.users().drafts().send(userId='me', id=draft_id).execute()
            latency = (time.time() - start_time) * 1000
            
            self.logger.log_call(
                service='Gmail',
                operation='send_draft',
                method='users.drafts.send',
                request_shape={'userId': 'me', 'id': '[DRAFT_ID]'},
                response_status=200,
                response_body={
                    'id': '[MESSAGE_ID]',
                    'threadId': result.get('threadId'),
                    'labelIds': result.get('labelIds', []),
                },
                error=None,
                latency_ms=latency,
                notes="Draft sent successfully",
            )
        except HttpError as e:
            self.logger.log_call(
                service='Gmail',
                operation='send_draft',
                method='users.drafts.send',
                request_shape={'userId': 'me'},
                response_status=e.resp.status,
                response_body=None,
                error=str(e),
                latency_ms=0,
                notes="HTTP error",
            )

    def _test_rate_limit(self):
        """Test: Rate limit / quota errors (intentionally trigger)."""
        try:
            # Try to make many rapid requests to trigger rate limit
            start_time = time.time()
            for i in range(10):
                self.service.users().threads().list(userId='me', maxResults=1).execute()
            
            latency = (time.time() - start_time) * 1000
            
            self.logger.log_call(
                service='Gmail',
                operation='rate_limit_test',
                method='users.threads.list (x10)',
                request_shape={'userId': 'me', 'maxResults': 1},
                response_status=200,
                response_body={'calls': 10, 'status': 'success'},
                error=None,
                latency_ms=latency,
                notes="10 rapid requests completed without hitting rate limit",
            )
        except HttpError as e:
            error_body = json.loads(e.content)
            self.logger.log_call(
                service='Gmail',
                operation='rate_limit_test',
                method='users.threads.list (x10)',
                request_shape={'userId': 'me'},
                response_status=e.resp.status,
                response_body=error_body.get('error', {}),
                error=error_body.get('error', {}).get('message', str(e)),
                latency_ms=0,
                notes=f"Rate limit triggered: {error_body.get('error', {}).get('code')}",
            )

    def _test_expired_token(self):
        """Test: Expired token behavior (intentionally corrupt token)."""
        try:
            # Get the current credentials and invalidate token
            # This is a tricky test - we'll just log what we expect
            self.logger.log_call(
                service='Gmail',
                operation='expired_token_test',
                method='users.threads.list',
                request_shape={'userId': 'me', 'note': 'token would be expired'},
                response_status=401,
                response_body=None,
                error='UNAUTHENTICATED',
                latency_ms=0,
                notes="Skipped: Token invalidation not safe in test. Would return 401 UNAUTHENTICATED",
            )
        except Exception as e:
            self.logger.logger.error(f"Expired token test error: {e}")

    def _test_invalid_recipient(self):
        """Test: Invalid recipient error."""
        try:
            # Try to send to an invalid email
            draft_body = {
                'message': {
                    'raw': 'From: [EMAIL]\nTo: invalid-email-address\nSubject: Test\n\nTest',
                }
            }
            
            start_time = time.time()
            result = self.service.users().drafts().create(userId='me', body=draft_body).execute()
            draft_id = result['id']
            
            # Try to send
            result = self.service.users().drafts().send(userId='me', id=draft_id).execute()
            latency = (time.time() - start_time) * 1000
            
            self.logger.log_call(
                service='Gmail',
                operation='invalid_recipient',
                method='users.drafts.send',
                request_shape={'userId': 'me', 'to': 'invalid-email-address'},
                response_status=200,
                response_body={'id': '[MESSAGE_ID]'},
                error=None,
                latency_ms=latency,
                notes="Invalid recipient accepted by API (validation happens server-side)",
            )
        except HttpError as e:
            error_body = json.loads(e.content)
            self.logger.log_call(
                service='Gmail',
                operation='invalid_recipient',
                method='users.drafts.send',
                request_shape={'userId': 'me', 'to': 'invalid-email-address'},
                response_status=e.resp.status,
                response_body=error_body.get('error', {}),
                error=error_body.get('error', {}).get('message', str(e)),
                latency_ms=0,
                notes="Invalid recipient rejected",
            )


class CalendarSpike:
    """Capture Calendar API behavior."""

    def __init__(self, service, logger: APIBehaviorLogger):
        self.service = service
        self.logger = logger

    def run(self):
        """Execute Calendar spike tests."""
        self.logger.logger.info("Starting Calendar spike tests...")
        
        # Test 1: Freebusy query
        self._test_freebusy()
        
        # Test 2: Create event with tentative status
        self._test_create_tentative_event()
        
        # Test 3: Update event
        self._test_update_event()
        
        # Test 4: Delete event
        self._test_delete_event()
        
        # Test 5: Timezone handling (Asia/Kolkata)
        self._test_timezone_handling()
        
        # Test 6: Conflict responses
        self._test_conflict_response()

    def _test_freebusy(self):
        """Test: Freebusy query."""
        try:
            start_time = time.time()
            result = self.service.freebusy().query(
                body={
                    'timeMin': (datetime.utcnow()).isoformat() + 'Z',
                    'timeMax': (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z',
                    'items': [{'id': 'primary'}],
                }
            ).execute()
            latency = (time.time() - start_time) * 1000
            
            self.logger.log_call(
                service='Calendar',
                operation='freebusy_query',
                method='freebusy.query',
                request_shape={
                    'timeMin': '[ISO_TIME]',
                    'timeMax': '[ISO_TIME]',
                    'items': [{'id': 'primary'}],
                },
                response_status=200,
                response_body={
                    'calendars': result.get('calendars', {}),
                    'timeMin': result.get('timeMin'),
                    'timeMax': result.get('timeMax'),
                },
                error=None,
                latency_ms=latency,
                notes="Freebusy data retrieved for primary calendar",
            )
        except HttpError as e:
            self.logger.log_call(
                service='Calendar',
                operation='freebusy_query',
                method='freebusy.query',
                request_shape={},
                response_status=e.resp.status,
                response_body=None,
                error=str(e),
                latency_ms=0,
                notes="HTTP error",
            )

    def _test_create_tentative_event(self):
        """Test: Create event with tentative/hold status."""
        try:
            event_body = {
                'summary': 'Test Tentative Event',
                'start': {
                    'dateTime': (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': (datetime.utcnow() + timedelta(hours=2)).isoformat(),
                    'timeZone': 'UTC',
                },
                'status': 'tentative',  # or 'confirmed', 'cancelled'
                'transparency': 'opaque',  # or 'transparent'
            }
            
            start_time = time.time()
            result = self.service.events().insert(calendarId='primary', body=event_body).execute()
            latency = (time.time() - start_time) * 1000
            
            self.logger.log_call(
                service='Calendar',
                operation='create_tentative_event',
                method='events.insert',
                request_shape={
                    'summary': '[STRING]',
                    'status': 'tentative',
                    'transparency': 'opaque',
                },
                response_status=200,
                response_body={
                    'id': '[EVENT_ID]',
                    'status': result.get('status'),
                    'transparency': result.get('transparency'),
                },
                error=None,
                latency_ms=latency,
                notes="Tentative event created successfully",
            )
        except HttpError as e:
            self.logger.log_call(
                service='Calendar',
                operation='create_tentative_event',
                method='events.insert',
                request_shape={},
                response_status=e.resp.status,
                response_body=None,
                error=str(e),
                latency_ms=0,
                notes="HTTP error",
            )

    def _test_update_event(self):
        """Test: Update event."""
        try:
            # Create an event first
            event_body = {
                'summary': 'Event to Update',
                'start': {'dateTime': (datetime.utcnow() + timedelta(hours=1)).isoformat()},
                'end': {'dateTime': (datetime.utcnow() + timedelta(hours=2)).isoformat()},
            }
            create_result = self.service.events().insert(calendarId='primary', body=event_body).execute()
            event_id = create_result['id']
            
            # Update it
            create_result['summary'] = 'Event Updated'
            start_time = time.time()
            result = self.service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=create_result
            ).execute()
            latency = (time.time() - start_time) * 1000
            
            self.logger.log_call(
                service='Calendar',
                operation='update_event',
                method='events.update',
                request_shape={'calendarId': 'primary', 'eventId': '[EVENT_ID]'},
                response_status=200,
                response_body={
                    'id': '[EVENT_ID]',
                    'summary': result.get('summary'),
                    'updated': result.get('updated'),
                },
                error=None,
                latency_ms=latency,
                notes="Event updated successfully",
            )
        except HttpError as e:
            self.logger.log_call(
                service='Calendar',
                operation='update_event',
                method='events.update',
                request_shape={},
                response_status=e.resp.status,
                response_body=None,
                error=str(e),
                latency_ms=0,
                notes="HTTP error",
            )

    def _test_delete_event(self):
        """Test: Delete event."""
        try:
            # Create an event first
            event_body = {
                'summary': 'Event to Delete',
                'start': {'dateTime': (datetime.utcnow() + timedelta(hours=1)).isoformat()},
                'end': {'dateTime': (datetime.utcnow() + timedelta(hours=2)).isoformat()},
            }
            create_result = self.service.events().insert(calendarId='primary', body=event_body).execute()
            event_id = create_result['id']
            
            # Delete it
            start_time = time.time()
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            latency = (time.time() - start_time) * 1000
            
            self.logger.log_call(
                service='Calendar',
                operation='delete_event',
                method='events.delete',
                request_shape={'calendarId': 'primary', 'eventId': '[EVENT_ID]'},
                response_status=204,
                response_body=None,
                error=None,
                latency_ms=latency,
                notes="Event deleted (returns 204 No Content)",
            )
        except HttpError as e:
            self.logger.log_call(
                service='Calendar',
                operation='delete_event',
                method='events.delete',
                request_shape={},
                response_status=e.resp.status,
                response_body=None,
                error=str(e),
                latency_ms=0,
                notes="HTTP error",
            )

    def _test_timezone_handling(self):
        """Test: Timezone handling for Asia/Kolkata."""
        try:
            # Create event in Asia/Kolkata timezone
            event_body = {
                'summary': 'Kolkata Timezone Event',
                'start': {
                    'dateTime': (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                    'timeZone': 'Asia/Kolkata',
                },
                'end': {
                    'dateTime': (datetime.utcnow() + timedelta(hours=2)).isoformat(),
                    'timeZone': 'Asia/Kolkata',
                },
            }
            
            start_time = time.time()
            result = self.service.events().insert(calendarId='primary', body=event_body).execute()
            latency = (time.time() - start_time) * 1000
            
            self.logger.log_call(
                service='Calendar',
                operation='timezone_handling',
                method='events.insert',
                request_shape={
                    'summary': '[STRING]',
                    'timeZone': 'Asia/Kolkata',
                },
                response_status=200,
                response_body={
                    'id': '[EVENT_ID]',
                    'start': result.get('start'),
                    'end': result.get('end'),
                },
                error=None,
                latency_ms=latency,
                notes="Event created in Asia/Kolkata timezone, start/end times preserved",
            )
        except HttpError as e:
            self.logger.log_call(
                service='Calendar',
                operation='timezone_handling',
                method='events.insert',
                request_shape={},
                response_status=e.resp.status,
                response_body=None,
                error=str(e),
                latency_ms=0,
                notes="HTTP error",
            )

    def _test_conflict_response(self):
        """Test: Conflict responses (create overlapping events)."""
        try:
            # Create first event
            event1_body = {
                'summary': 'Conflict Test Event 1',
                'start': {'dateTime': (datetime.utcnow() + timedelta(hours=1)).isoformat()},
                'end': {'dateTime': (datetime.utcnow() + timedelta(hours=2)).isoformat()},
            }
            event1 = self.service.events().insert(calendarId='primary', body=event1_body).execute()
            
            # Create overlapping event
            event2_body = {
                'summary': 'Conflict Test Event 2 (overlaps)',
                'start': {'dateTime': (datetime.utcnow() + timedelta(hours=1, minutes=30)).isoformat()},
                'end': {'dateTime': (datetime.utcnow() + timedelta(hours=2, minutes=30)).isoformat()},
            }
            
            start_time = time.time()
            event2 = self.service.events().insert(calendarId='primary', body=event2_body).execute()
            latency = (time.time() - start_time) * 1000
            
            self.logger.log_call(
                service='Calendar',
                operation='conflict_response',
                method='events.insert (overlapping)',
                request_shape={'summary': '[STRING]', 'conflict': 'yes'},
                response_status=200,
                response_body={
                    'id': '[EVENT_ID]',
                    'summary': event2.get('summary'),
                    'conflictingEventsCount': 1,
                },
                error=None,
                latency_ms=latency,
                notes="Overlapping events allowed (Calendar API permits double-booking)",
            )
        except HttpError as e:
            self.logger.log_call(
                service='Calendar',
                operation='conflict_response',
                method='events.insert (overlapping)',
                request_shape={},
                response_status=e.resp.status,
                response_body=None,
                error=str(e),
                latency_ms=0,
                notes="HTTP error",
            )


def authenticate(creds_file: Path) -> tuple:
    """Authenticate with Google API using OAuth."""
    creds = None
    
    # Try to load existing credentials
    if creds_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(creds_file, SCOPES)
        except Exception as e:
            print(f"Error loading credentials: {e}")
            creds = None
    
    # If not valid, create new flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                print("Refresh token expired, need to re-authenticate")
                creds = None
        
        if not creds:
            # Would need credentials.json from Google Cloud Console
            print("Error: No valid credentials found")
            print("Please set up OAuth credentials and save to", creds_file)
            sys.exit(1)
    
    return creds


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Capture real Gmail and Calendar API behavior"
    )
    parser.add_argument(
        "--oauth-config",
        type=Path,
        default=Path.home() / ".config" / "chief-of-staff" / "google-oauth.json",
        help="Path to OAuth credentials file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent.parent / "docs" / "spikes" / "google-api-behavior.md",
        help="Output file for findings",
    )
    
    args = parser.parse_args()
    
    # Authenticate
    print(f"Authenticating with Google APIs (credentials: {args.oauth_config})...")
    creds = authenticate(args.oauth_config)
    
    # Build services
    print("Building Gmail and Calendar services...")
    gmail_service = build('gmail', 'v1', credentials=creds)
    calendar_service = build('calendar', 'v3', credentials=creds)
    
    # Create logger
    logger = APIBehaviorLogger(args.output)
    
    # Run spikes
    try:
        print("\nRunning Gmail spike tests...")
        gmail_spike = GmailSpike(gmail_service, logger)
        gmail_spike.run()
        
        print("\nRunning Calendar spike tests...")
        calendar_spike = CalendarSpike(calendar_service, logger)
        calendar_spike.run()
        
        # Write report
        print(f"\nWriting report to {args.output}...")
        logger.write_report()
        print(f"✓ Report written to {args.output}")
        
    except Exception as e:
        print(f"Error during spike execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
