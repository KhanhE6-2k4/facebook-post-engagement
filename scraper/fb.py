import logging

from curl_cffi import requests

from get_post_info import HEADERS, parse_facebook_stats
from scraper.config import CONFIG
from scraper.rate_limiter import limiter

log = logging.getLogger(__name__)


def fetch_post_stats(url):
  """Trả về dict react/comment/share, hoặc None nếu không lấy được."""
  cfg = CONFIG["request"]
  for attempt in range(cfg["retries"] + 1):
    try:
      with limiter.slot():
        response = requests.get(
            url,
            headers=HEADERS,
            impersonate=cfg["impersonate"],
            timeout=cfg["timeout_sec"],
        )
      if response.status_code == 200:
        return parse_facebook_stats(response.text)
      log.warning("%s -> HTTP %s (lần %d)", url, response.status_code, attempt + 1)
    except Exception as e:
      log.warning("%s -> lỗi %s (lần %d)", url, e, attempt + 1)
  return None
