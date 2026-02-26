"""Google API authentication helper for Calendar & Tasks."""
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
CREDENTIALS_FILE = os.path.join(PROJECT_ROOT, "credentials.json")
TOKEN_FILE = os.path.join(PROJECT_ROOT, "token.json")

# Multi-account support: account label -> token file
ACCOUNTS = {
    "primary": TOKEN_FILE,
    "huriye": os.path.join(PROJECT_ROOT, "token_huriye.json"),
    "mahirkurt": os.path.join(PROJECT_ROOT, "token_mahirkurt.json"),
}

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    # Google Classroom scopes
    "https://www.googleapis.com/auth/classroom.courses",
    "https://www.googleapis.com/auth/classroom.coursework.students",
    "https://www.googleapis.com/auth/classroom.announcements",
    "https://www.googleapis.com/auth/classroom.rosters",
    "https://www.googleapis.com/auth/classroom.profile.emails",
]


def get_credentials(scopes=None, token_file=None,
                     login_hint=None):
    """Get or refresh OAuth2 credentials.

    Args:
        scopes: OAuth scopes (defaults to SCOPES).
        token_file: Path to token JSON file (defaults to TOKEN_FILE).
        login_hint: Email hint for account selection.
    """
    scopes = scopes or SCOPES
    token_file = token_file or TOKEN_FILE
    creds = None

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(
            token_file, scopes,
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, scopes,
            )
            extra = {}
            if login_hint:
                extra["login_hint"] = login_hint

            creds = flow.run_local_server(
                port=8090,
                open_browser=False,
                prompt="consent",
                access_type="offline",
                **extra,
            )

        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return creds


def get_calendar_service(token_file=None):
    """Build a Calendar API service client."""
    creds = get_credentials(token_file=token_file)
    return build("calendar", "v3", credentials=creds)


def get_tasks_service(token_file=None):
    """Build a Tasks API service client."""
    creds = get_credentials(token_file=token_file)
    return build("tasks", "v1", credentials=creds)


if __name__ == "__main__":
    import sys
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    account = sys.argv[1] if len(sys.argv) > 1 else None
    token = ACCOUNTS.get(account) if account else TOKEN_FILE
    hint = None
    if account == "huriye":
        hint = "huriye.murzoglu@gmail.com"
    elif account == "mahirkurt":
        hint = "drmahirkurt@gmail.com"

    print("Authenticating with Google...")
    print(f"Token file: {token}")
    if hint:
        print(f"Account hint: {hint}")
    print(
        "If no browser opens, visit the URL "
        "printed below and authorize."
    )
    creds = get_credentials(
        token_file=token, login_hint=hint,
    )
    print(f"\nToken saved to {token}")
    print(f"Token valid: {creds.valid}")

    # Quick test
    cal = build("calendar", "v3", credentials=creds)
    calendars = cal.calendarList().list().execute()
    items = calendars.get("items", [])
    print(f"\nCalendars found: {len(items)}")
    for c in items:
        print(f"  - {c['summary']} ({c['id']})")

    tasks = build("tasks", "v1", credentials=creds)
    task_lists = tasks.tasklists().list().execute()
    items = task_lists.get("items", [])
    print(f"\nTask lists found: {len(items)}")
    for t in items:
        print(f"  - {t['title']} ({t['id']})")
