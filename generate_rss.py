from datetime import datetime
import json
import ssl
import urllib.request
import xml.etree.ElementTree as ET

# 天文台警告摘要 RSS 網址
rss_url = "https://rss.weather.gov.hk/rss/WeatherWarningBulletin_uc.xml"
output_filename = "warnings_data.json"

print("正在從香港天文台下載天氣警告摘要...")

try:
  context = ssl._create_unverified_context()
  req = urllib.request.urlopen(rss_url, context=context)
  xml_data = req.read()

  root = ET.fromstring(xml_data)
  channel = root.find("channel")

  warnings_list = []
  for item in channel.findall("item"):
    title = item.find("title").text if item.find("title") is not None else ""
    description = item.find("description").text if item.find("description") is not None else ""
    pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
    
    warnings_list.append({
        "title": title,
        "description": description,
        "pubDate": pub_date
    })

  warning_json_data = {
      "updateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      "warnings": warnings_list
  }

  with open(output_filename, "w", encoding="utf-8") as f:
    json.dump(warning_json_data, f, ensure_ascii=False, indent=4)

  print(f"✅ 成功：已生成 {output_filename}，共抓取到 {len(warnings_list)} 筆警告提示。")

except Exception as e:
  print(f"❌ 發生錯誤：{e}")