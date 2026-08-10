from datetime import datetime
import json
import ssl
import urllib.request

# 天文台 15 分鐘平均紫外線指數 CSV 網址
url = "https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_15min_uvindex_uc.csv"
output_filename = "uv_data.json"

print("正在從香港天文台下載最新紫外線資料...")

try:
  context = ssl._create_unverified_context()
  req = urllib.request.urlopen(url, context=context)
  lines = [line.decode("utf-8-sig").strip() for line in req.readlines()]

  valid_rows = []
  # 從頭到尾讀取所有有效行
  for line in lines[1:]:  # 跳過標題行
    if not line:
      continue
    cols = [c.replace('"', "").strip() for c in line.split(",")]
    if len(cols) >= 2 and cols[1] != "" and cols[1] != "-":
      valid_rows.append(cols)

  if len(valid_rows) > 0:
    # 取得最接近當前時間的最後一行（即最新資料）
    latest = valid_rows[-1]
    time_col = latest[0]  # 例如 08:45 或 202608100845
    uv_val = latest[1]  # 例如 3

    # 格式化時間顯示格式 (若格式為 HH:MM 或長數字，統一轉為好看的格式)
    if len(time_col) >= 12:
      time_col = f"{time_col[8:10]}:{time_col[10:12]}"

    try:
      num_uv = float(uv_val)
      if num_uv < 3:
        desc = "低"
      elif num_uv < 6:
        desc = "中等"
      elif num_uv < 8:
        desc = "高"
      elif num_uv < 11:
        desc = "甚高"
      else:
        desc = "極高"
    except ValueError:
      desc = "無數據"

    uv_data = {"time": time_col, "value": uv_val, "description": desc}

    with open(output_filename, "w", encoding="utf-8") as json_file:
      json.dump(uv_data, json_file, ensure_ascii=False, indent=4)

    print(
        f"✅ 成功：已生成 {output_filename} (時間: {time_col}, 紫外線: {uv_val})"
    )
  else:
    print("❌ 錯誤：找不到有效的紫外線資料。")

except Exception as e:
  print(f"❌ 發生錯誤：{e}")