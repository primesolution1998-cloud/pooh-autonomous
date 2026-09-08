import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from integrations.google_sheets_writer import append_record, find_matching_rows, safe_update_row

DEFAULT_SPREADSHEET_ID = "1qai1d83M9-cjHZQEN30au6NAFG3X44K4uZFo7nVAbzg"
AUDIT_FILE = Path("projects/ytc_write_audit.json")
INDIA = ZoneInfo("Asia/Kolkata")


def _spreadsheet_id():
    return os.getenv("YTC_SPREADSHEET_ID", DEFAULT_SPREADSHEET_ID).strip()


def _norm(text):
    return " ".join(str(text or "").strip().lower().replace("–", "-").replace("—", "-").split())


def _command_hash(text):
    return hashlib.sha256(_norm(text).encode("utf-8")).hexdigest()[:24]


def _load_audit():
    if not AUDIT_FILE.exists():
        return []
    try:
        return json.loads(AUDIT_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _audit(entry):
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = _load_audit()
    data.append(entry)
    AUDIT_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _recent_duplicate(text, minutes=10):
    wanted = _command_hash(text)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    for item in reversed(_load_audit()):
        if item.get("command_hash") != wanted or item.get("status") != "EXECUTED":
            continue
        try:
            when = datetime.fromisoformat(item["timestamp"])
        except Exception:
            continue
        if when >= cutoff:
            return item
    return None


def _approved(text):
    value = _norm(text)
    return any(token in value for token in ("confirm", "confirmed", "approved", "approve", "execute now", "final karo"))


def looks_like_ytc_sheet_command(text):
    value = _norm(text)
    if "ytc" in value:
        return True
    signals = ("student", "admission", "batch", "fee", "paid", "demo", "inquiry", "follow-up", "followup", "lead")
    return sum(signal in value for signal in signals) >= 2


def _mobile(text):
    match = re.search(r"(?:\+?91[\s-]?)?([6-9]\d{9})\b", text)
    return match.group(1) if match else None


def _amount(text):
    patterns = (
        r"₹\s*([0-9]+(?:\.[0-9]+)?)",
        r"\b([0-9]+(?:\.[0-9]+)?)\s*(?:paid|pay|rs\.?|rupees?)\b",
        r"(?:paid|pay)\s*(?:₹|rs\.?|rupees?)?\s*([0-9]+(?:\.[0-9]+)?)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return float(match.group(1))
    return None


def _total_fee(text):
    match = re.search(r"(?:total\s*fee|fee\s*total)\s*(?:₹|rs\.?|rupees?)?\s*([0-9]+(?:\.[0-9]+)?)", text, flags=re.I)
    return float(match.group(1)) if match else None


def _batch(text):
    match = re.search(
        r"\b(\d{1,2}(?::\d{2})?\s*(?:to|-|–)\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b",
        text,
        flags=re.I,
    )
    if not match:
        return None
    return re.sub(r"\s*(?:-|–)\s*", " to ", match.group(1)).strip()


def _name(text):
    match = re.search(r"(?:student\s+)?([A-Za-z][A-Za-z .'-]{1,60}?)\s+ko\b", text, flags=re.I)
    if match:
        candidate = " ".join(match.group(1).split())
        candidate = re.sub(r"^(?:ytc|confirm|approved|approve)\s+", "", candidate, flags=re.I).strip()
        if candidate:
            return candidate
    match = re.search(r"\bname\s*[:=-]\s*([A-Za-z][A-Za-z .'-]{1,60})", text, flags=re.I)
    return " ".join(match.group(1).split()) if match else None


def _payment_mode(text):
    value = _norm(text)
    modes = {
        "gpay": "GPay",
        "google pay": "GPay",
        "phonepe": "PhonePe",
        "phone pe": "PhonePe",
        "upi": "UPI",
        "cash": "Cash",
        "bank": "Bank Transfer",
    }
    for token, label in modes.items():
        if token in value:
            return label
    return ""


def _status_value(text):
    value = _norm(text)
    for token, label in (
        ("inactive", "Inactive"),
        ("dropped", "Dropped"),
        ("active", "Active"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("on hold", "On Hold"),
        ("positive", "Positive"),
        ("negative", "Negative"),
        ("present", "Present"),
        ("absent", "Absent"),
    ):
        if token in value:
            return label
    return None


def _to_number(value):
    try:
        return float(str(value).replace(",", "").strip() or 0)
    except Exception:
        return 0.0


def _money(value):
    if value is None:
        return ""
    return int(value) if float(value).is_integer() else round(float(value), 2)


def _find_unique(sheet, name=None, mobile=None, mobile_column=None, name_column=None):
    sid = _spreadsheet_id()
    match = {}
    if mobile and mobile_column:
        match[mobile_column] = mobile
    elif name and name_column:
        match[name_column] = name
    else:
        return None, "Student/lead identifier missing"

    rows = find_matching_rows(sid, sheet, match)
    if not rows:
        return None, f"No matching record found in {sheet}"
    if len(rows) > 1:
        return None, f"Multiple matching records found in {sheet}; mobile number required"
    return rows[0], None


def _row_dict(match):
    return {
        header: match["row"][i] if i < len(match["row"]) else ""
        for i, header in enumerate(match["headers"])
    }


def _preview(action, details):
    return {
        "status": "AWAITING_APPROVAL",
        "action": action,
        "details": details,
        "instruction": "Send the same command with CONFIRM to execute the Sheet change.",
    }


def _execute_student_update(text, task_id):
    sid = _spreadsheet_id()
    name = _name(text)
    mobile = _mobile(text)
    amount = _amount(text)
    batch = _batch(text)
    total_fee = _total_fee(text)
    mode = _payment_mode(text)

    if not name and not mobile:
        return {"status": "FAILED", "reason": "Student name or mobile number is required"}

    admission, error = _find_unique("Admission", name, mobile, "Mobile", "Student Name")
    if error and "No matching" in error:
        if not (name and mobile and batch and total_fee is not None):
            return {
                "status": "FAILED",
                "reason": "New admission requires name, mobile, batch and total fee. Paid amount is optional.",
            }
        paid = amount or 0
        pending = max(total_fee - paid, 0)
        today = datetime.now(INDIA).strftime("%d-%m-%Y")
        record = {
            "Admission Date": today,
            "Student Name": name,
            "Mobile": mobile,
            "Batch": batch,
            "Admission Fee": _money(total_fee),
            "Paid Amount": _money(paid),
            "Pending Amount": _money(pending),
            "Payment Mode": mode,
            "Students Status": "Active",
        }
        if not _approved(text):
            return _preview("CREATE_ADMISSION", record)
        duplicate = _recent_duplicate(text)
        if duplicate:
            return {"status": "DUPLICATE_BLOCKED", "reason": "Same confirmed command already executed recently", "audit": duplicate}
        result = append_record(sid, "Admission", record)
        fee_record = {
            "Admission Date": today,
            "Student Name": name,
            "Mobile Number": mobile,
            "Batch Time": batch,
            "Total Fee": _money(total_fee),
            "Paid Amount": _money(paid),
            "Pending Amount": _money(pending),
            "Fee Received Date": today if paid else "",
            "Payment Mode": mode,
            "Fee Status": "Paid" if pending <= 0 else "Partially Paid" if paid else "Pending",
            "Payment Entry": _money(paid) if paid else "",
        }
        fee_result = append_record(sid, "Fee Management", fee_record)
        audit = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "command_hash": _command_hash(text),
            "status": "EXECUTED",
            "action": "CREATE_ADMISSION",
            "targets": [result.get("updated_range"), fee_result.get("updated_range")],
            "student": name,
            "mobile_last4": mobile[-4:],
        }
        _audit(audit)
        return {"status": "EXECUTED", "action": "CREATE_ADMISSION", "admission": result, "fee": fee_result}
    if error:
        return {"status": "FAILED", "reason": error}

    current = _row_dict(admission)
    updates = {}
    fee_updates = {}
    if batch:
        updates["Batch"] = batch
        fee_updates["Batch Time"] = batch
    if amount is not None:
        new_paid = _to_number(current.get("Paid Amount")) + amount
        total = _to_number(current.get("Admission Fee"))
        updates["Paid Amount"] = _money(new_paid)
        updates["Pending Amount"] = _money(max(total - new_paid, 0))

    if not updates:
        return {"status": "FAILED", "reason": "No supported YTC change detected (batch/payment)"}

    details = {"student": current.get("Student Name"), "admission_row": admission["row_number"], "updates": updates}
    if not _approved(text):
        return _preview("UPDATE_STUDENT", details)

    duplicate = _recent_duplicate(text)
    if duplicate:
        return {"status": "DUPLICATE_BLOCKED", "reason": "Same confirmed command already executed recently", "audit": duplicate}

    admission_result = safe_update_row(sid, "Admission", admission["row_number"], updates)

    fee_match, fee_error = _find_unique("Fee Management", name, mobile, "Mobile Number", "Student Name")
    fee_result = None
    if not fee_error:
        fee_current = _row_dict(fee_match)
        if amount is not None:
            fee_paid = _to_number(fee_current.get("Paid Amount")) + amount
            fee_total = _to_number(fee_current.get("Total Fee"))
            fee_updates.update({
                "Paid Amount": _money(fee_paid),
                "Pending Amount": _money(max(fee_total - fee_paid, 0)),
                "Fee Received Date": datetime.now(INDIA).strftime("%d-%m-%Y"),
                "Payment Entry": _money(amount),
                "Fee Status": "Paid" if fee_total and fee_paid >= fee_total else "Partially Paid",
            })
            if mode:
                fee_updates["Payment Mode"] = mode
        if fee_updates:
            fee_result = safe_update_row(sid, "Fee Management", fee_match["row_number"], fee_updates)

    audit = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "command_hash": _command_hash(text),
        "status": "EXECUTED",
        "action": "UPDATE_STUDENT",
        "student": current.get("Student Name"),
        "mobile_last4": str(current.get("Mobile", ""))[-4:],
        "admission_row": admission["row_number"],
        "admission_changes": admission_result,
        "fee_changes": fee_result,
    }
    _audit(audit)
    return {"status": "EXECUTED", "action": "UPDATE_STUDENT", "admission": admission_result, "fee": fee_result}


def _execute_lead_or_demo(text, task_id):
    sid = _spreadsheet_id()
    value = _norm(text)
    mobile = _mobile(text)
    name = _name(text)
    status = _status_value(text)
    if not status:
        return {"status": "FAILED", "reason": "Status value not detected"}

    if "demo" in value:
        sheet, mobile_col, name_col = "Demo Booking", "Mobile", "Student Name"
        target_col = "Demo Result" if status in ("Positive", "Negative") else "Attendance" if status in ("Present", "Absent") else "Demo Status"
    elif "inquiry" in value or "followup" in value or "follow-up" in value:
        sheet, mobile_col, name_col = "Inquiry CRM", "Mobile", "Name"
        target_col = "Call Status"
    else:
        sheet, mobile_col, name_col = "Leads", "Mobile Number", "Student Name"
        target_col = "Status"

    match, error = _find_unique(sheet, name, mobile, mobile_col, name_col)
    if error:
        return {"status": "FAILED", "reason": error}
    details = {"sheet": sheet, "row": match["row_number"], "column": target_col, "value": status}
    if not _approved(text):
        return _preview("UPDATE_STATUS", details)
    duplicate = _recent_duplicate(text)
    if duplicate:
        return {"status": "DUPLICATE_BLOCKED", "reason": "Same confirmed command already executed recently", "audit": duplicate}
    result = safe_update_row(sid, sheet, match["row_number"], {target_col: status})
    _audit({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "command_hash": _command_hash(text),
        "status": "EXECUTED",
        "action": "UPDATE_STATUS",
        "sheet": sheet,
        "row": match["row_number"],
        "changes": result,
    })
    return {"status": "EXECUTED", "action": "UPDATE_STATUS", "result": result}


def execute_ytc_sheet_command(text, task_id):
    if not looks_like_ytc_sheet_command(text):
        return None
    value = _norm(text)
    if any(token in value for token in ("lead", "demo", "inquiry", "followup", "follow-up")) and any(
        token in value for token in ("active", "inactive", "dropped", "completed", "cancelled", "positive", "negative", "present", "absent")
    ):
        return _execute_lead_or_demo(text, task_id)
    return _execute_student_update(text, task_id)
