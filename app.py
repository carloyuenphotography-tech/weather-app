import io
import zipfile
import csv
import requests
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# CSDI 靜態下載連結
CSDI_ZIP_URL = "https://static.csdi.gov.hk/csdi-webpage/download/04db0982a43f561db9e922cd082b09f9/geojson"

@app.route('/')
def home():
    return "HKO Humidity API 正在運行中！"

@app.route('/humidity', methods=['GET'])
def get_humidity():
    try:
        # 1. 下載 CSDI 的 ZIP 檔
        response = requests.get(CSDI_ZIP_URL)
        if response.status_code != 200:
            return jsonify({"error": "無法從 CSDI 下載資料"}), 500

        stations_data = []

        # 2. 在記憶體中解壓縮
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            file_list = z.namelist()
            target_file = next((f for f in file_list if f.endswith('.json') or f.endswith('.geojson')), None)
            
            if not target_file:
                return jsonify({"error": "壓縮檔內找不到 geojson 檔案"}), 404

            # 3. 讀取 GeoJSON 內容
            import json
            with z.open(target_file) as f:
                geo_data = json.loads(f.read().decode('utf-8'))
                
                # 4. 遍歷每個氣象站，自動去抓取其對應的 CSV 數據
                for feature in geo_data.get('features', []):
                    props = feature.get('properties', {})
                    station_name = props.get('AutomaticWeatherStation_en') or props.get('STATION_NAME') or '未知站點'
                    data_url = props.get('Data_url') # 指向 CSV 的連結

                    humidity = "資料未明"
                    timestamp = "即時"

                    # 如果有 CSV 連結，直接在後端幫您下載並解析濕度
                    if data_url:
                        try:
                            csv_res = requests.get(data_url, timeout=3)
                            if csv_res.status_code == 200:
                                # 解析 CSV 內容
                                csv_content = csv_res.content.decode('utf-8', errors='ignore')
                                csv_reader = csv.DictReader(io.StringIO(csv_content))
                                
                                # 通常 CSV 的最後一行是最新數據
                                rows = list(csv_reader)
                                if rows:
                                    latest_row = rows[-1]
                                    # 尋找濕度與時間欄位
                                    for key, val in latest_row.items():
                                        if key and ('humidity' in key.lower() or 'rh' in key.lower()) and val:
                                            humidity = f"{val}%"
                                        if key and ('time' in key.lower() or 'date' in key.lower()) and val:
                                            timestamp = val
                        except Exception as csv_err:
                            print(f"讀取 {station_name} CSV 失敗: {csv_err}")

                    stations_data.append({
                        "station": station_name,
                        "humidity": humidity,
                        "time": timestamp
                    })

        return jsonify(stations_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
