import logging
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo

import gspread
from gspread.utils import column_letter_to_index

from scraper.config import CONFIG
from scraper.fb import fetch_post_stats
from scraper.sheets import open_worksheet

log = logging.getLogger(__name__)


OPERATORS = ("+", "-", "*", "/")


def parse_score_formula(data):
  """Kiểm tra công thức gửi từ web: {"weights": {react, comment, share}, "operators": [op1, op2]}.
  Trả về công thức đã chuẩn hóa; raise ValueError nếu không hợp lệ."""
  try:
    weights = {k: float(data["weights"][k]) for k in ("react", "comment", "share")}
    operators = list(data["operators"])
  except (KeyError, TypeError, ValueError):
    raise ValueError("Công thức tính điểm không hợp lệ: hệ số phải là số")
  if not all(math.isfinite(v) for v in weights.values()):
    raise ValueError("Công thức tính điểm không hợp lệ: hệ số phải là số")
  if len(operators) != 2 or any(op not in OPERATORS for op in operators):
    raise ValueError("Công thức tính điểm không hợp lệ: phép tính phải là + - * /")
  return {"weights": weights, "operators": operators}


def build_score_formula(formula, row_num):
  """Công thức sheet cho một dòng, vd "=(1*C2)+(2*D2)+(3*E2)".
  Mỗi "hệ số x biến" được bọc ngoặc để a*C / b*E là (a*C)/(b*E), không bị tính trái sang phải."""
  cols = CONFIG["sheet"]["columns"]
  w = formula["weights"]
  op1, op2 = formula["operators"]
  return (
      f"=({w['react']:g}*{cols['react']}{row_num})"
      f"{op1}({w['comment']:g}*{cols['comment']}{row_num})"
      f"{op2}({w['share']:g}*{cols['share']}{row_num})"
  )


def _rename_to_run_time(ws):
  cfg = CONFIG["sheet"]
  title = datetime.now(ZoneInfo(cfg["timezone"])).strftime(cfg["title_format"])
  try:
    ws.update_title(title)
  except gspread.exceptions.APIError as e:  # vd trùng tên với tab khác: không chặn việc cào
    log.warning("Không đổi được tên trang tính thành '%s': %s", title, e)


def run_job(sheet_url, formula, job):
  """Đọc link theo batch, cào song song, ghi kết quả từng batch lên sheet. Cập nhật tiến độ vào `job`."""
  cols = CONFIG["sheet"]["columns"]
  first_row = CONFIG["sheet"]["header_row"] + 1
  batch_size = CONFIG["batch"]["size"]

  ws = open_worksheet(sheet_url)
  _rename_to_run_time(ws)
  last_row = len(ws.col_values(column_letter_to_index(cols["link"])))
  job["total"] = max(0, last_row - first_row + 1)

  with ThreadPoolExecutor(max_workers=CONFIG["workers"]["n_workers"]) as pool:
    for start in range(first_row, last_row + 1, batch_size):
      end = min(start + batch_size - 1, last_row)
      links = ws.get(f"{cols['link']}{start}:{cols['link']}{end}")
      rows = []
      for i, row_num in enumerate(range(start, end + 1)):
        link = links[i][0].strip() if i < len(links) and links[i] else ""
        if link:
          rows.append((row_num, link))

      results = pool.map(lambda r: fetch_post_stats(r[1]), rows)

      updates = []
      for (row_num, link), stats in zip(rows, results):
        # Luôn ghi đè cột Điểm bằng công thức từ web để điểm khớp công thức đang dùng
        updates.append({"range": f"{cols['score']}{row_num}", "values": [[build_score_formula(formula, row_num)]]})
        if stats is None:
          job["failed"] += 1
          continue
        updates.append({
            "range": f"{cols['react']}{row_num}:{cols['share']}{row_num}",
            "values": [[stats["react_count"], stats["comment_count"], stats["share_count"]]],
        })
      if updates:
        ws.batch_update(updates, value_input_option="USER_ENTERED")

      job["processed"] = end - first_row + 1
      log.info("Batch %d-%d xong (%d/%d)", start, end, job["processed"], job["total"])
