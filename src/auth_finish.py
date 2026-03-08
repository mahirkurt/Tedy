"""Complete OAuth flow by exchanging the redirect URL for a token.

Usage:
    python src/auth_finish.py <account> "<redirect_url>"

Example:
    python src/auth_finish.py huriye "http://localhost:8090/?state=...&code=...&scope=..."
"""
import json
import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
CREDENTIALS_FILE = os.path.join(PROJECT_ROOT, "credentials.json")

ACCOUNTS = {
    "primary": os.path.join(PROJECT_ROOT, "token.json"),
    "huriye": os.path.join(PROJECT_ROOT, "token_huriye.json"),
    "mahirkurt": os.path.join(PROJECT_ROOT, "token_mahirkurt.json"),
}

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/classroom.courses",
    "https://www.googleapis.com/auth/classroom.coursework.students",
    "https://www.googleapis.com/auth/classroom.announcements",
    "https://www.googleapis.com/auth/classroom.rosters",
    "https://www.googleapis.com/auth/classroom.profile.emails",
]


def main():
    if len(sys.argv) < 3:
        print("Usage: python src/auth_finish.py <account> <redirect_url>")
        print("Accounts:", ", ".join(ACCOUNTS.keys()))
        sys.exit(1)

    account = sys.argv[1]
    redirect_url = sys.argv[2]

    token_file = ACCOUNTS.get(account)
    if not token_file:
        print(f"Unknown account: {account}")
        print("Available:", ", ".join(ACCOUNTS.keys()))
        sys.exit(1)

    print(f"Completing OAuth for: {account}")
    print(f"Token file: {token_file}")

    flow = InstalledAppFlow.from_client_secrets_file(
        CREDENTIALS_FILE, SCOPES,
    )
    flow.redirect_uri = "http://localhost:8090/"

    flow.fetch_token(authorization_response=redirect_url)
    creds = flow.credentials

    with open(token_file, "w") as f:
        f.write(creds.to_json())

    print(f"\nToken saved to {token_file}")
    print(f"Token valid: {creds.valid}")

    # Quick verification
    cal = build("calendar", "v3", credentials=creds)
    calendars = cal.calendarList().list().execute()
    items = calendars.get("items", [])
    print(f"\nCalendars found: {len(items)}")
    for c in items:
        print(f"  - {c['summary']}")

    print("\nAuth complete!")


if __name__ == "__main__":
    main()
