from datetime import datetime
import json
import os
import ssl
import urllib.request

# 天文台 15 分鐘平均紫外線指數 CSV 網址
url = "https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_15min_uvindex_uc.csv"
output_filename = "uv_data.json"

print("正在從香港天文台下載最新紫外線資料...")

try:
  # 建立忽略 SSL 憑證驗證的 Context，解決憑證報錯
  context = ssl._create_unverified_context()

  req = urllib.request.urlopen(url, context=context)
  lines = [line.decode("utf-8-sig").strip() for line in req.readlines()]

  if len(lines) > 1:
    latest_line = lines[-1]
    cols = [c.replace('"', "").strip() for c in latest_line.split(",")]

    time_col = cols[0] if len(cols) > 0 else "--"
    uv_val = cols[1] if len(cols) > 1 else "--"

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
    print("❌ 錯誤：CSV 內容為空。")

except Exception as e:
  print(f"❌ 發生錯誤：{e}")