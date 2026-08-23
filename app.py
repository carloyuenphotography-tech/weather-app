import io
import zipfile
import csv
import requests
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

CSDI_ZIP_URL = "https://static.csdi.gov.hk/csdi-webpage/download/04db0982a43f561db9e922cd082b09f9/geojson"

@app.route('/')
def home():
    return "HKO Weather API 正在運行中！"

@app.route('/humidity', methods=['GET'])
def get_humidity():
    try:
        response = requests.get(CSDI_ZIP_URL)
        if response.status_code != 200:
            return jsonify({"error": "無法從 CSDI 下載資料"}), 500

        stations_data = []

        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            file_list = z.namelist()
            target_file = next((f for f in file_list if f.endswith('.json') or f.endswith('.geojson')), None)
            
            if not target_file:
                return jsonify({"error": "壓縮檔內找不到 geojson 檔案"}), 404

            import json
            with z.open(target_file) as f:
                geo_data = json.loads(f.read().decode('utf-8'))
                
                for feature in geo_data.get('features', []):
                    props = feature.get('properties', {})
                    geometry = feature.get('geometry', {})
                    coords = geometry.get('coordinates', [])
                    
                    lng = coords[0] if len(coords) > 0 else None
                    lat = coords[1] if len(coords) > 1 else None

                    station_name = props.get('AutomaticWeatherStation_en') or props.get('STATION_NAME') or '未知站點'
                    data_url = props.get('Data_url')

                    humidity = "資料未明"
                    temperature = "資料未明"
                    timestamp = "即時"

                    if data_url:
                        try:
                            csv_res = requests.get(data_url, timeout=3)
                            if csv_res.status_code == 200:
                                csv_content = csv_res.content.decode('utf-8', errors='ignore')
                                csv_reader = csv.DictReader(io.StringIO(csv_content))
                                rows = list(csv_reader)
                                if rows:
                                    latest_row = rows[-1]
                                    for key, val in latest_row.items():
                                        k_lower = key.lower() if key else ""
                                        # 抓取濕度
                                        if ('humidity' in k_lower or 'rh' in k_lower) and val:
                                            humidity = f"{val}%"
                                        # 抓取氣溫
                                        elif ('temp' in k_lower or 'temperature' in k_lower) and val:
                                            temperature = f"{val}°C"
                                        # 抓取時間
                                        if ('time' in k_lower or 'date' in k_lower) and val:
                                            timestamp = val
                        except Exception:
                            pass

                    stations_data.append({
                        "station": station_name,
                        "temperature": temperature,
                        "humidity": humidity,
                        "time": timestamp,
                        "lat": lat,
                        "lng": lng
                    })

        return jsonify(stations_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
