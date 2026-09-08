import os
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv()

READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"


def _credentials():
    credentials_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
    if not credentials_file:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_FILE is not configured")

    path = Path(credentials_file).expanduser().resolve()
    if not path.exists():
        raise RuntimeError(f"Google service account file not found: {path}")

    return Credentials.from_service_account_file(
        str(path),
        scopes=[READONLY_SCOPE],
    )


def sheets_service():
    return build("sheets", "v4", credentials=_credentials(), cache_discovery=False)


def read_range(spreadsheet_id: str, range_name: str):
    if not spreadsheet_id.strip():
        raise ValueError("spreadsheet_id is required")
    if not range_name.strip():
        raise ValueError("range_name is required")

    service = sheets_service()
    response = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_name)
        .execute()
    )
    return response.get("values", [])


def list_sheet_titles(spreadsheet_id: str):
    if not spreadsheet_id.strip():
        raise ValueError("spreadsheet_id is required")

    service = sheets_service()
    response = (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, fields="sheets.properties.title")
        .execute()
    )
    return [sheet["properties"]["title"] for sheet in response.get("sheets", [])]
