import io
import zipfile
import csv
import requests
from flask import Flask, jsonify
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
CORS(app)

TEMP_ZIP_URL = "https://static.csdi.gov.hk/csdi-webpage/download/f8e1bd259b4d58218b8ea5a07b874472/geojson"
HUMIDITY_ZIP_URL = "https://static.csdi.gov.hk/csdi-webpage/download/04db0982a43f561db9e922cd082b09f9/geojson"

def fetch_single_station(feature, val_type):
    props = feature.get('properties', {})
    geometry = feature.get('geometry', {})
    coords = geometry.get('coordinates', [])
    
    lng = coords[0] if len(coords) > 0 else None
    lat = coords[1] if len(coords) > 1 else None

    station_name = props.get('AutomaticWeatherStation_en') or props.get('STATION_NAME') or props.get('name') or '未知站點'
    data_url = props.get('Data_url')

    val_str = "資料未明"
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
                        if val_type == 'temp' and ('temp' in k_lower or 'temperature' in k_lower) and val:
                            val_str = val
                        elif val_type == 'humidity' and ('humidity' in k_lower or 'rh' in k_lower) and val:
                            val_str = val
                        if ('time' in k_lower or 'date' in k_lower) and val:
                            timestamp = val
        except Exception:
            pass

    return station_name, {
        "value": val_str,
        "time": timestamp,
        "lat": lat,
        "lng": lng
    }

def fetch_station_data(zip_url, val_type):
    data_map = {}
    try:
        response = requests.get(zip_url, timeout=5)
        if response.status_code != 200:
            return data_map

        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            file_list = z.namelist()
            target_file = next((f for f in file_list if f.endswith('.json') or f.endswith('.geojson')), None)
            if not target_file:
                return data_map

            import json
            with z.open(target_file) as f:
                geo_data = json.loads(f.read().decode('utf-8'))
                features = geo_data.get('features', [])

                # 使用多執行緒同時下載所有站點的 CSV，大幅提速避免逾時
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(fetch_single_station, feature, val_type) for feature in features]
                    for future in as_completed(futures):
                        s_name, s_info = future.result()
                        if s_name:
                            data_map[s_name] = s_info
    except Exception as e:
        print(f"Error fetching {zip_url}: {e}")
    return data_map

@app.route('/')
def home():
    return "HKO Weather API 正在運行中！"

@app.route('/humidity', methods=['GET'])
def get_weather():
    try:
        # 同時並行抓取溫度與濕度
        temp_data = fetch_station_data(TEMP_ZIP_URL, 'temp')
        humid_data = fetch_station_data(HUMIDITY_ZIP_URL, 'humidity')

        all_stations = set(list(temp_data.keys()) + list(humid_data.keys()))
        
        combined_result = []
        for station in all_stations:
            t_info = temp_data.get(station, {})
            h_info = humid_data.get(station, {})

            lat = t_info.get('lat') or h_info.get('lat')
            lng = t_info.get('lng') or h_info.get('lng')
            time_val = t_info.get('time') or h_info.get('time') or '即時'

            t_val = t_info.get('value', '資料未明')
            temperature = f"{t_val}°C" if t_val != "資料未明" else "資料未明"

            h_val = h_info.get('value', '資料未明')
            humidity = f"{h_val}%" if h_val != "資料未明" else "資料未明"

            combined_result.append({
                "station": station,
                "temperature": temperature,
                "humidity": humidity,
                "time": time_val,
                "lat": lat,
                "lng": lng
            })

        return jsonify(combined_result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
