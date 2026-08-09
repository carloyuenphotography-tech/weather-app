import csv
from datetime import datetime, timedelta
import json

# 讀取 CSV 檔案
filename = 'tbt2026.csv'  # 請確認您的檔案名稱
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
end_date = today + timedelta(days=30)

tide_data = {}

try:
  with open(filename, mode='r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    header = next(reader)  # 跳過標題行

    for row in reader:
      if len(row) < 3:
        continue
      date_str, time_str, height_str = (
          row[0].strip(),
          row[1].strip(),
          row[2].strip(),
      )

      # 嘗試解析日期
      parsed_date = None
      for fmt in ('%Y-%m-%d', '%Y%m%d', '%d/%m/%Y'):
        try:
          parsed_date = datetime.strptime(date_str, fmt)
          break
        except ValueError:
          continue

      if parsed_date:
        parsed_date = parsed_date.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        if today <= parsed_date <= end_date:
          key = parsed_date.strftime('%Y-%m-%d')
          if key not in tide_data:
            tide_data[key] = []
          tide_data[key].append({'time': time_str, 'height': height_str})

  # 輸出成前端可以直接讀取的 JSON 檔
  with open('tide_30days.json', 'w', encoding='utf-8') as json_file:
    json.dump(tide_data, json_file, ensure_ascii=False, indent=4)
  print('成功：未來 30 日潮汐資料已成功轉換為 tide_30days.json！')

except Exception as e:
  print(f'讀取失敗：{e}')