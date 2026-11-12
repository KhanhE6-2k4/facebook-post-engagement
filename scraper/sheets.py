import json
import os
import re

import gspread

SHEET_URL_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9-_]+)")
GID_RE = re.compile(r"[#&?]gid=(\d+)")


def parse_sheet_url(url):
  """Trả về (spreadsheet_id, gid hoặc None). Raise ValueError nếu URL không hợp lệ."""
  m = SHEET_URL_RE.search(url or "")
  if not m:
    raise ValueError("URL Google Sheet không hợp lệ")
  gid = GID_RE.search(url)
  return m.group(1), (int(gid.group(1)) if gid else None)


def _client():
  raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS")
  if raw:
    return gspread.service_account_from_dict(json.loads(raw))
  path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH")
  if path:
    return gspread.service_account(filename=path)
  raise RuntimeError(
      "Chưa cấu hình service account (GOOGLE_SERVICE_ACCOUNT_CREDENTIALS hoặc GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH)"
  )


def open_worksheet(url):
  spreadsheet_id, gid = parse_sheet_url(url)
  client = _client()
  try:
    spreadsheet = client.open_by_key(spreadsheet_id)
    return spreadsheet.get_worksheet_by_id(gid) if gid is not None else spreadsheet.sheet1
  except (gspread.exceptions.APIError, gspread.exceptions.SpreadsheetNotFound) as e:
    email = getattr(client.http_client.auth, "service_account_email", "service account")
    raise RuntimeError(
        f"Không mở được sheet ({e}). Hãy để sheet ở chế độ 'Bất kỳ ai có đường liên kết - Người chỉnh sửa' "
        f"hoặc chia sẻ quyền chỉnh sửa cho {email}"
    ) from e
