import csv
from datetime import datetime, timedelta
import json
import os

# 1. 取得今天的日期與 30 天後的日期
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
end_date = today + timedelta(days=30)
current_year = today.year

# 2. 自動選擇對應年份的 CSV 檔案（例如 2026 年讀取 tbt2026.csv）
filename = f"tbt{current_year}.csv"

tide_data = {}

if not os.path.exists(filename):
  print(f"錯誤：找不到檔案 {filename}，請確認是否已上載至相同目錄。")
else:
  try:
    # 使用 utf-8-sig 以防 CSV 帶有 BOM 標頭
    with open(filename, mode="r", encoding="utf-8-sig") as f:
      reader = csv.reader(f)
      header = next(reader, None)  # 略過標題列

      for row in reader:
        if len(row) < 3:
          continue
        date_str = row[0].strip().replace('"', "")
        time_str = row[1].strip().replace('"', "")
        height_str = row[2].strip().replace('"', "")

        # 嘗試解析多種常見的日期格式
        parsed_date = None
        for fmt in ("%Y-%m-%d", "%Y%m%d", "%d/%m/%Y", "%Y/%m/%d"):
          try:
            parsed_date = datetime.strptime(date_str, fmt)
            break
          except ValueError:
            continue

        if parsed_date:
          parsed_date = parsed_date.replace(
              hour=0, minute=0, second=0, microsecond=0
          )
          # 篩選由今日起至未來 30 日內的資料
          if today <= parsed_date <= end_date:
            key = parsed_date.strftime("%Y-%m-%d")
            if key not in tide_data:
              tide_data[key] = []
            tide_data[key].append({"time": time_str, "height": height_str})

    # 3. 輸出成 JSON 檔案
    output_filename = "tide_30days.json"
    with open(output_filename, "w", encoding="utf-8") as json_file:
      json.dump(tide_data, json_file, ensure_ascii=False, indent=4)

    print(f"成功：已成功讀取 {filename} 並生成 {output_filename}！")

  except Exception as e:
    print(f"讀取或解析過程發生錯誤：{e}")