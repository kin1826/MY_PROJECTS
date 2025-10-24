import json
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# --- Cấu hình ---
NOTION_TOKEN = ""  # Thay bằng token của bạn
DATABASE_ID = ""  # Thay bằng database ID của bạn
DATA_FILE = Path(__file__).parent / "tasks.json"

def fetch_notion_tasks():
    """Lấy danh sách task từ Notion Calendar"""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    res = requests.post(url, headers=headers)
    res.raise_for_status()
    data = res.json()

    today_str = datetime.now().strftime("%Y-%m-%d")
    tasks_today = []

    for page in data.get("results", []):
        props = page.get("properties", {})

        title = ""
        if "Name" in props and props["Name"]["title"]:
            title = props["Name"]["title"][0]["plain_text"]

        # property Date (kiểu Date) trong Notion
        date_info = props.get("Date", {}).get("date")
        if not date_info:
            continue

        start = date_info.get("start")
        end = date_info.get("end")

        # lọc task hôm nay
        if start and start.startswith(today_str):
            start_time = datetime.fromisoformat(start).strftime("%H:%M")
            end_time = datetime.fromisoformat(end).strftime("%H:%M") if end else "00:00"

            tasks_today.append({
                "id": page.get("id"),
                "title": title or "Untitled",
                "time": start_time,
                "to": end_time
            })

    return today_str, tasks_today


def save_tasks_to_json():
    """Ghi dữ liệu vào data.json"""
    today, tasks = fetch_notion_tasks()

    # load file cũ (nếu có)
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            all_data = json.load(f)
    else:
        all_data = {}
 
    all_data[today] = tasks

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Đã lưu {len(tasks)} task vào {DATA_FILE.name}")

