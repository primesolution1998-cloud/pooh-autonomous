import os
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv()

WRITE_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


def _credentials():
    credentials_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
    if not credentials_file:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_FILE is not configured")

    path = Path(credentials_file).expanduser().resolve()
    if not path.exists():
        raise RuntimeError(f"Google service account file not found: {path}")

    return Credentials.from_service_account_file(str(path), scopes=[WRITE_SCOPE])


def sheets_service():
    return build("sheets", "v4", credentials=_credentials(), cache_discovery=False)


def _column_letter(index):
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def read_table(spreadsheet_id, sheet_title, formula_mode=False):
    service = sheets_service()
    kwargs = {
        "spreadsheetId": spreadsheet_id,
        "range": sheet_title,
    }
    if formula_mode:
        kwargs["valueRenderOption"] = "FORMULA"
    response = service.spreadsheets().values().get(**kwargs).execute()
    return response.get("values", [])


def find_matching_rows(spreadsheet_id, sheet_title, match):
    rows = read_table(spreadsheet_id, sheet_title)
    if not rows:
        return []
    headers = rows[0]
    index = {name: i for i, name in enumerate(headers)}
    unknown = [key for key in match if key not in index]
    if unknown:
        raise ValueError(f"Unknown columns in {sheet_title}: {unknown}")

    def norm(value, key):
        text = str(value or "").strip().casefold()
        if "mobile" in key.casefold() or "phone" in key.casefold():
            return "".join(ch for ch in text if ch.isdigit())[-10:]
        return " ".join(text.split())

    matches = []
    for row_number, row in enumerate(rows[1:], start=2):
        ok = True
        for key, expected in match.items():
            actual = row[index[key]] if index[key] < len(row) else ""
            if norm(actual, key) != norm(expected, key):
                ok = False
                break
        if ok:
            matches.append({"row_number": row_number, "row": row, "headers": headers})
    return matches


def safe_update_row(spreadsheet_id, sheet_title, row_number, updates):
    if row_number < 2:
        raise ValueError("Refusing to modify header row")

    values = read_table(spreadsheet_id, sheet_title)
    formulas = read_table(spreadsheet_id, sheet_title, formula_mode=True)
    if not values:
        raise RuntimeError(f"Sheet is empty: {sheet_title}")

    headers = values[0]
    index = {name: i for i, name in enumerate(headers)}
    unknown = [key for key in updates if key not in index]
    if unknown:
        raise ValueError(f"Unknown columns in {sheet_title}: {unknown}")

    existing = values[row_number - 1] if row_number - 1 < len(values) else []
    formula_row = formulas[row_number - 1] if row_number - 1 < len(formulas) else []
    before = {}
    applied = {}
    skipped_formula_columns = []
    data = []

    for column, value in updates.items():
        i = index[column]
        old = existing[i] if i < len(existing) else ""
        formula = formula_row[i] if i < len(formula_row) else ""
        before[column] = old
        if isinstance(formula, str) and formula.startswith("="):
            skipped_formula_columns.append(column)
            continue
        cell = f"'{sheet_title}'!{_column_letter(i + 1)}{row_number}"
        data.append({"range": cell, "values": [[value]]})
        applied[column] = value

    if not data:
        return {
            "status": "NO_CHANGE",
            "row_number": row_number,
            "before": before,
            "applied": {},
            "skipped_formula_columns": skipped_formula_columns,
        }

    service = sheets_service()
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"valueInputOption": "USER_ENTERED", "data": data},
    ).execute()
    return {
        "status": "UPDATED",
        "row_number": row_number,
        "before": before,
        "applied": applied,
        "skipped_formula_columns": skipped_formula_columns,
    }


def append_record(spreadsheet_id, sheet_title, record):
    rows = read_table(spreadsheet_id, sheet_title)
    if not rows:
        raise RuntimeError(f"Sheet is empty: {sheet_title}")
    headers = rows[0]
    unknown = [key for key in record if key not in headers]
    if unknown:
        raise ValueError(f"Unknown columns in {sheet_title}: {unknown}")
    row = [record.get(header, "") for header in headers]
    service = sheets_service()
    response = service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_title}'",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()
    return {
        "status": "APPENDED",
        "updated_range": response.get("updates", {}).get("updatedRange"),
        "record": record,
    }
