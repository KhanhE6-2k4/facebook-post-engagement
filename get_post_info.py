from bs4 import BeautifulSoup
import json
import os
import re
from curl_cffi import requests

# HEADERS = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
#     "Accept-Language": "en-US,en;q=0.9",
# }

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


# def parse_facebook_stats(html_content):
#   """Hàm parse chuẩn xác sử dụng Regex trực tiếp trên toàn bộ nội dung HTML"""
#   # 1. Lấy tổng số reactions (khớp cả tiếng Anh lẫn tiếng Việt)
#   react_match = re.search(
#       r'aria-hidden="true"[^>]*><span><span[^>]*>([\d,\.]+)<\/span><\/span>',
#       html_content,
#   )
#   react_count = (
#       react_match.group(1).replace(",", "").replace(".", "")
#       if react_match
#       else "0"
#   )

#   # 2. Lấy số lượng Comments (bắt cả "comments" lẫn "bình luận")
#   comment_match = re.search(
#       r"([\d,\.]+)\s+(?:comments|bình luận)", html_content, re.IGNORECASE
#   )
#   comment_count = (
#       comment_match.group(1).replace(",", "").replace(".", "")
#       if comment_match
#       else "0"
#   )

#   # 3. Lấy số lượng Shares (bắt cả "shares", "lượt chia sẻ" hoặc "chia sẻ")
#   share_match = re.search(
#       r"([\d,\.]+)\s+(?:shares|lượt chia sẻ|chia sẻ)",
#       html_content,
#       re.IGNORECASE,
#   )
#   share_count = (
#       share_match.group(1).replace(",", "").replace(".", "")
#       if share_match
#       else "0"
#   )

#   return {
#       "react_count": int(react_count) if react_count.isdigit() else 0,
#       "comment_count": int(comment_count) if comment_count.isdigit() else 0,
#       "share_count": int(share_count) if share_count.isdigit() else 0,
#   }

def parse_display_count(text):
  """Chuyển chuỗi hiển thị của FB sang số nguyên (chuỗi): "350" -> "350",
  "1,234" -> "1234", "1.7K" / "1,7K" -> "1700", "2M" -> "2000000".
  Số có hậu tố K/M chỉ là xấp xỉ do FB đã làm tròn."""
  m = re.fullmatch(r"\s*([\d.,]+)\s*([KkMm]?)\s*", text)
  if not m:
    return "0"
  number, suffix = m.groups()
  if not suffix:
    return number.replace(",", "").replace(".", "")
  multiplier = 1000 if suffix in "Kk" else 1000000
  return str(int(float(number.replace(",", ".")) * multiplier))


def parse_facebook_stats(html_content):
  """Hàm parse tối ưu dựa trên các mẫu chuỗi dữ liệu JSON ngầm của Facebook

  (Lấy phần tử đầu tiên khớp theo đúng yêu cầu).
  """

  # 1. Parse Reaction
  # Ưu tiên mẫu 1: "reaction_count":{"count":350,...} (số nguyên chính xác)
  # Dự phòng mẫu 2: "i18n_reaction_count":"350" — chuỗi hiển thị, có thể là "1.7K".
  # Lấy đúng giá trị đầu tiên (là tổng) rồi quy đổi K/M; các giá trị sau là
  # số của từng loại reaction nên không được khớp sang.
  react_count = "0"
  react_match = re.search(
      r'"reaction_count"\s*:\s*\{\s*"count"\s*:\s*([\d]+)', html_content
  )
  if react_match:
    react_count = react_match.group(1)
  else:
    react_match_alt = re.search(
        r'"i18n_reaction_count"\s*:\s*"([^"]*)"', html_content
    )
    if react_match_alt:
      react_count = parse_display_count(react_match_alt.group(1))

  # 2. Parse Comments (Mẫu: "comments":{"total_count":8})
  comment_count = "0"
  comment_match = re.search(
      r'"comments"\s*:\s*\{\s*"total_count"\s*:\s*([\d]+)', html_content
  )
  if comment_match:
    comment_count = comment_match.group(1)

  # 3. Parse Shares
  # Ưu tiên mẫu 1: "share_count":{"count":232,...} (số nguyên chính xác)
  # Dự phòng mẫu 2: "i18n_share_count":"232" (có thể là "1.2K", xem ghi chú ở trên)
  share_count = "0"
  share_match = re.search(
      r'"share_count"\s*:\s*\{\s*"count"\s*:\s*([\d]+)', html_content
  )
  if share_match:
    share_count = share_match.group(1)
  else:
    share_match_alt = re.search(
        r'"i18n_share_count"\s*:\s*"([^"]*)"', html_content
    )
    if share_match_alt:
      share_count = parse_display_count(share_match_alt.group(1))

  # Chuẩn hóa dữ liệu sang dạng số nguyên (xóa dấu phẩy/chấm nếu có)
  clean_react = react_count.replace(",", "").replace(".", "")
  clean_comment = comment_count.replace(",", "").replace(".", "")
  clean_share = share_count.replace(",", "").replace(".", "")

  return {
      "react_count": int(clean_react) if clean_react.isdigit() else 0,
      "comment_count": int(clean_comment) if clean_comment.isdigit() else 0,
      "share_count": int(clean_share) if clean_share.isdigit() else 0,
  }


def process_links_from_json(json_file_path):
  # Tạo thư mục chứa các file HTML debug nếu chưa có
  debug_dir = "debug_htmls"
  if not os.path.exists(debug_dir):
    os.makedirs(debug_dir)

  with open(json_file_path, "r", encoding="utf-8") as f:
    links_data = json.load(f)

  results = []
  for index, item in enumerate(links_data, start=1):
    url = item.get("url")
    if not url:
      continue

    print(f"[{index}] Đang cào: {url}")
    try:
      # Sử dụng impersonate="chrome120" để giả lập vân tay trình duyệt Chrome
      response = requests.get(url, headers=HEADERS, impersonate="chrome120", timeout=10)

      # --- BƯỚC DEBUG: LƯU HTML TRUNG GIAN ---
      # Tạo tên file an toàn dựa trên số thứ tự để tránh lỗi ký tự đặc biệt trong URL
      safe_filename = f"post_{index}.html"
      file_path = os.path.join(debug_dir, safe_filename)

      with open(file_path, "w", encoding="utf-8") as html_file:
        html_file.write(response.text)
      print(f" -> Đã lưu HTML vào: {file_path} (Status: {response.status_code})")
      # --------------------------------------

      if response.status_code == 200:
        stats = parse_facebook_stats(response.text)
        results.append({"url": url, **stats})
      else:
        results.append(
            {
                "url": url,
                "react_count": 0,
                "comment_count": 0,
                "share_count": 0,
            }
        )
    except Exception as e:
      print(f"Lỗi khi cào {url}: {e}")
      results.append(
          {"url": url, "react_count": 0, "comment_count": 0, "share_count": 0}
      )

  # Lưu kết quả tổng hợp ra file JSON
  with open("facebook_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=4)

  print(
      "\nHoàn tất! Kiểm tra thư mục 'debug_htmls/' để xem các file HTML đã tải."
  )


# Chạy chương trình:
if __name__ == "__main__":
  process_links_from_json('post_urls.json')
