import logging
import os
import threading
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from scraper.config import CONFIG
from scraper.fb import proxy_url
from scraper.runner import parse_score_formula, run_job
from scraper.sheets import parse_sheet_url

load_dotenv()  # nạp .env (nếu có) vào os.environ; không ghi đè biến đã đặt sẵn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.info("FB proxy: %s", "đã cấu hình" if proxy_url() else "chưa cấu hình (FB_PROXY_URL trống)")

PROXY_UNSUPPORTED = "Hiện tại proxy chưa được hỗ trợ"

app = Flask(__name__)
jobs = {}


def _worker(job_id, sheet_url, formula, use_proxy):
  job = jobs[job_id]
  try:
    run_job(sheet_url, formula, use_proxy, job)
    job["status"] = "done"
  except Exception as e:
    logging.exception("Job %s lỗi", job_id)
    job["status"] = "error"
    job["message"] = str(e)


@app.get("/")
def index():
  return render_template("index.html", score=CONFIG["score"],
                         proxy_available=bool(proxy_url()), proxy_unsupported=PROXY_UNSUPPORTED)


@app.post("/api/run")
def run():
  data = request.get_json(silent=True) or {}
  sheet_url = str(data.get("sheet_url", "")).strip()
  try:
    parse_sheet_url(sheet_url)
    formula = parse_score_formula(data.get("formula"))
  except ValueError as e:
    return jsonify({"error": str(e)}), 400
  use_proxy = data.get("use_proxy") is True
  if use_proxy and not proxy_url():
    return jsonify({"error": PROXY_UNSUPPORTED}), 400
  job_id = uuid.uuid4().hex
  jobs[job_id] = {"status": "running", "processed": 0, "total": 0, "failed": 0,
                  "sheet_url": sheet_url, "message": ""}
  threading.Thread(target=_worker, args=(job_id, sheet_url, formula, use_proxy), daemon=True).start()
  return jsonify({"job_id": job_id})


@app.get("/api/status/<job_id>")
def status(job_id):
  job = jobs.get(job_id)
  if job is None:
    return jsonify({"error": "Không tìm thấy job"}), 404
  return jsonify(job)


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
