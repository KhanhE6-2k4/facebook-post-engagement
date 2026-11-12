# FB Post Scraper

Web app (Flask, deploy trên PaaS bất kỳ hỗ trợ Python): nhập URL Google Sheet → cào react/comment/share
các link bài FB ở cột B → ghi vào cột C/D/E, ghi công thức điểm (người dùng chọn trên web) vào cột F.

## Coding guidelines
@docs/karpathy-guidelines.md

## Project notes
- Tham số hay đổi (công thức điểm, batch size, n_workers, rate limit) để trong `config.yaml`, không hard-code.
- Logic parse FB nằm ở `get_post_info.py` (`parse_facebook_stats`) — tái dùng, không viết lại.
- Credential service account lấy từ env `GOOGLE_SERVICE_ACCOUNT_CREDENTIALS`/`GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH`, không commit. Local: đặt trong `.env` (mẫu: `.env.example`), `app.py` tự nạp bằng `python-dotenv`.
- Proxy residential cho request tới FB: env `FB_PROXY_URL` (tùy chọn); người dùng bật/tắt trên web. Request tới Google Sheets không đi qua proxy.
- Không gắn với nền tảng deploy cụ thể nào: chỉ dựa vào `requirements.txt`, `Procfile`, env vars và `$PORT`.
- Chạy local: `python app.py`; production: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 120`.
