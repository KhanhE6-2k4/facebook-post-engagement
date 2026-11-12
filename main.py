import json
import re


def parse_facebook_stats(html_content):
  # 1. Lấy tổng số reactions (khớp cả tiếng Anh lẫn tiếng Việt)
  react_match = re.search(
      r'aria-hidden="true"[^>]*><span><span[^>]*>([\d,\.]+)<\/span><\/span>',
      html_content,
  )
  react_count = (
      react_match.group(1).replace(",", "").replace(".", "")
      if react_match
      else "0"
  )

  # 2. Lấy số lượng Comments (bắt cả "comments" lẫn "bình luận")
  comment_match = re.search(
      r"([\d,\.]+)\s+(?:comments|bình luận)", html_content, re.IGNORECASE
  )
  comment_count = (
      comment_match.group(1).replace(",", "").replace(".", "")
      if comment_match
      else "0"
  )

  # 3. Lấy số lượng Shares (bắt cả "shares", "lượt chia sẻ" hoặc "chia sẻ")
  share_match = re.search(
      r"([\d,\.]+)\s+(?:shares|lượt chia sẻ|chia sẻ)",
      html_content,
      re.IGNORECASE,
  )
  share_count = (
      share_match.group(1).replace(",", "").replace(".", "")
      if share_match
      else "0"
  )

  return {
      "react_count": int(react_count) if react_count.isdigit() else 0,
      "comment_count": int(comment_count) if comment_count.isdigit() else 0,
      "share_count": int(share_count) if share_count.isdigit() else 0,
  }


# --- Kiểm tra thử với đoạn HTML tiếng Việt của bạn ---

html_path = "link3.html"
with open(html_path, "r", encoding="utf-8") as f:
    html_sample = f.read()

print(parse_facebook_stats(html_sample))
# Kết quả trả về chính xác: {'react_count': 23, 'comment_count': 4, 'share_count': 6}
