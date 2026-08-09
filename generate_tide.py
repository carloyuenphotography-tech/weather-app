import csv
from datetime import datetime, timedelta
import json
import os

today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
end_date = today + timedelta(days=30)
current_year = today.year

filename = f"tbt{current_year}.csv"
print(f"正在讀取檔案: {filename}")
print(f"篩選目標區間: {today.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}\n")

tide_data = {}
row_count = 0
matched_count = 0

if not os.path.exists(filename):
  print(f"❌ 錯誤：找不到檔案 {filename}")
else:
  try:
    with open(filename, mode="r", encoding="utf-8-sig") as f:
      reader = csv.reader(f)
      header = next(reader, None)  # 跳過標題

      for row in reader:
        row_count += 1
        if len(row) < 4:
          continue

        try:
          # 根據你的 CSV 結構：第 0 欄是 Month，第 1 欄是 Date
          month_str = row[0].strip().replace('"', "")
          day_str = row[1].strip().replace('"', "")

          month = int(month_str)
          day = int(day_str)

          # 組合出今天的完整日期物件 (以當前年份 2026 為準)
          parsed_date = datetime(current_year, month, day)
          parsed_date = parsed_date.replace(
              hour=0, minute=0, second=0, microsecond=0
          )

          # 檢查是否在今天起未來 30 天內
          if today <= parsed_date <= end_date:
            key = parsed_date.strftime("%Y-%m-%d")
            if key not in tide_data:
              tide_data[key] = []

            # 一天有多組時間與高度 (從第 2 欄開始，每 2 欄為一組：Time, Height)
            for i in range(2, len(row) - 1, 2):
              time_str = row[i].strip().replace('"', "")
              height_str = row[i + 1].strip().replace('"', "")

              if time_str and height_str and time_str != "":
                tide_data[key].append({"time": time_str, "height": height_str})
                matched_count += 1

        except ValueError:
          continue

    print(f"總共掃描了 {row_count} 行資料。")
    print(f"成功配對到今天起 30 天內的潮汐記錄筆數: {matched_count} 筆。")

    # 輸出成 JSON 檔案
    with open("tide_30days.json", "w", encoding="utf-8") as json_file:
      json.dump(tide_data, json_file, ensure_ascii=False, indent=4)
    print("✅ 成功：已順利生成包含正確資料的 tide_30days.json！")

  except Exception as e:
    print(f"❌ 發生錯誤：{e}")