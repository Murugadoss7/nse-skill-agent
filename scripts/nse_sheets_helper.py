#!/usr/bin/env python3
"""
Google Sheets helper — handles token refresh + API calls.
Usage:
    python3 nse_sheets_helper.py --list-tabs
    python3 nse_sheets_helper.py --read Portfolio
    python3 nse_sheets_helper.py --append 'Trade Ideas' '["2026-06-01","RELIANCE","BUY","1350-1365","1420","1320","7","swing","Crude drop"]'
"""
import json
import sys
import os
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SHEET_ID = "1J2OpZyiiGnDMlXJgExR1HgnJmyIH2HjIC5siHoGFbZ4"
TOKEN_PATH = Path.home() / ".hermes" / "google_token.json"
CLIENT_SECRET_PATH = Path.home() / ".hermes" / "google_client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_sheets_service():
    """Get authenticated Sheets service with auto-refresh."""
    creds = None
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH) as f:
            token_data = json.load(f)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)

    # If expired and refresh token exists, auto-refresh
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save refreshed token
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
            print("[sheets-helper] Token refreshed automatically", file=sys.stderr)
        except Exception as e:
            print(f"[sheets-helper] Token refresh failed: {e}", file=sys.stderr)
            print("[sheets-helper] Run: python3 nse_sheets_helper.py --reauth", file=sys.stderr)
            return None

    if not creds or not creds.valid:
        print("[sheets-helper] No valid credentials", file=sys.stderr)
        return None

    return build("sheets", "v4", credentials=creds)


def list_tabs():
    service = get_sheets_service()
    if not service:
        return []
    sheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    return [s["properties"]["title"] for s in sheet["sheets"]]


def read_tab(tab_name):
    service = get_sheets_service()
    if not service:
        return []
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=tab_name
    ).execute()
    return result.get("values", [])


def append_row(tab_name, row_data):
    service = get_sheets_service()
    if not service:
        return False
    result = service.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range=tab_name,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row_data]},
    ).execute()
    return result.get("updates", {}).get("updatedRows", 0) > 0


def reauth():
    """Generate auth URL for re-authentication."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
    creds = flow.run_local_server(port=0, open_browser=False)
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())
    print(f"[sheets-helper] ✅ Token saved to {TOKEN_PATH}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "--list-tabs":
        tabs = list_tabs()
        print("\n".join(tabs))

    elif cmd == "--read":
        tab = sys.argv[2] if len(sys.argv) > 2 else "Portfolio"
        rows = read_tab(tab)
        for row in rows[:5]:
            print(" | ".join(str(c) for c in row))
        print(f"\n... {len(rows)} rows total")

    elif cmd == "--append":
        tab = sys.argv[2] if len(sys.argv) > 2 else "Trade Ideas"
        row = json.loads(sys.argv[3]) if len(sys.argv) > 3 else []
        ok = append_row(tab, row)
        print("✅ Appended" if ok else "❌ Failed")

    elif cmd == "--reauth":
        reauth()

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
