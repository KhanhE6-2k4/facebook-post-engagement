import logging
import os

from curl_cffi import requests

from get_post_info import HEADERS, parse_facebook_stats
from scraper.config import CONFIG
from scraper.rate_limiter import limiter

log = logging.getLogger(__name__)


def proxy_url():
  """URL proxy (residential) từ env FB_PROXY_URL; None nếu chưa cấu hình."""
  return os.environ.get("FB_PROXY_URL") or None


def fetch_post_stats(url, use_proxy=False):
  """Trả về dict react/comment/share, hoặc None nếu không lấy được.
  use_proxy=True: gửi request tới FB qua FB_PROXY_URL (người gọi phải kiểm tra proxy đã cấu hình)."""
  cfg = CONFIG["request"]
  proxies = {"http": proxy_url(), "https": proxy_url()} if use_proxy else None
  for attempt in range(cfg["retries"] + 1):
    try:
      with limiter.slot():
        response = requests.get(
            url,
            headers=HEADERS,
            impersonate=cfg["impersonate"],
            timeout=cfg["timeout_sec"],
            proxies=proxies,
        )
      if response.status_code == 200:
        return parse_facebook_stats(response.text)
      log.warning("%s -> HTTP %s (lần %d)", url, response.status_code, attempt + 1)
    except Exception as e:
      log.warning("%s -> lỗi %s (lần %d)", url, e, attempt + 1)
  return None
