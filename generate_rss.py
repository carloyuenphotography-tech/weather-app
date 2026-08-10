from datetime import datetime
import json
import ssl
import urllib.request
import xml.etree.ElementTree as ET

# 天文台即時天氣報告 RSS 網址
rss_url = "https://rss.weather.gov.hk/rss/CurrentWeather_uc.xml"
output_filename = "rss_data.json"

print("正在從香港天文台下載 RSS 天氣報告...")

try:
  # 建立忽略 SSL 憑證驗證的 Context
  context = ssl._create_unverified_context()
  req = urllib.request.urlopen(rss_url, context=context)
  xml_data = req.read()

  # 解析 XML
  root = ET.fromstring(xml_data)
  channel = root.find("channel")

  # 抓取 RSS 基本資訊
  channel_title = channel.find("title").text if channel.find("title") is not None else "香港天文台天氣報告"
  
  items_list = []
  # 抓取所有新聞/報告項目 (item)
  for item in channel.findall("item"):
    title = item.find("title").text if item.find("title") is not None else ""
    description = item.find("description").text if item.find("description") is not None else ""
    pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
    
    items_list.append({
        "title": title,
        "description": description,
        "pubDate": pub_date
    })

  # 整理成最終的 JSON 結構
  rss_json_data = {
      "channelTitle": channel_title,
      "updateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      "items": items_list
  }

  with open(output_filename, "w", encoding="utf-8") as f:
    json.dump(rss_json_data, f, ensure_ascii=False, indent=4)

  print(f"✅ 成功：已生成 {output_filename}，共抓取到 {len(items_list)} 筆報告。")

except Exception as e:
  print(f"❌ 發生錯誤：{e}")