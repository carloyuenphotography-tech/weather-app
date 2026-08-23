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

    # 提取中英文站名
    station_name_en = props.get('AutomaticWeatherStation_en') or props.get('STATION_NAME') or props.get('name') or 'Unknown'
    station_name_cn = props.get('AutomaticWeatherStation_sc') or props.get('AutomaticWeatherStation_tc') or station_name_en
    data_url = props.get('Data_url')

    val_str = None
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
                            try:
                                val_str = float(val)
                            except:
                                pass
                        elif val_type == 'humidity' and ('humidity' in k_lower or 'rh' in k_lower) and val:
                            try:
                                val_str = float(val)
                            except:
                                pass
                        if ('time' in k_lower or 'date' in k_lower) and val:
                            timestamp = val
        except Exception:
            pass

    return station_name_en, {
        "name_cn": station_name_cn,
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

                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(fetch_single_station, feature, val_type) for feature in features]
                    for future in as_completed(futures):
                        s_en, s_info = future.result()
                        if s_en:
                            data_map[s_en] = s_info
    except Exception as e:
        print(f"Error fetching {zip_url}: {e}")
    return data_map

@app.route('/')
def home():
    return "HKO Weather API 正在運行中！"

@app.route('/humidity', methods=['GET'])
def get_weather():
    try:
        temp_data = fetch_station_data(TEMP_ZIP_URL, 'temp')
        humid_data = fetch_station_data(HUMIDITY_ZIP_URL, 'humidity')

        all_stations = set(list(temp_data.keys()) + list(humid_data.keys()))
        
        combined_result = []
        humidities = []
        temperatures = []

        radiation_cooling_stations = []
        target_cooling_places = ["Ta Kwu Ling", "Shek Kong", "Wetland Park", "Sai Kung", "打鼓嶺", "石崗", "濕地公園", "西貢"]

        for station in all_stations:
            t_info = temp_data.get(station, {})
            h_info = humid_data.get(station, {})

            lat = t_info.get('lat') or h_info.get('lat')
            lng = t_info.get('lng') or h_info.get('lng')
            time_val = t_info.get('time') or h_info.get('time') or '即時'
            station_cn = t_info.get('name_cn') or h_info.get('name_cn') or station

            t_val = t_info.get('value')
            h_val = h_info.get('value')

            if t_val is not None:
                temperatures.append(t_val)
                temp_str = f"{t_val}°C"
            else:
                temp_str = "資料未明"

            if h_val is not None:
                humidities.append(h_val)
                humid_str = f"{h_val}%"
            else:
                humid_str = "資料未明"

            # 輻射冷卻檢測邏輯：內陸空曠處氣溫明顯偏低
            if any(p.lower() in station_cn.lower() or p.lower() in station.lower() for p in target_cooling_places):
                if t_val is not None:
                    radiation_cooling_stations.append({"station": station_cn, "temp": t_val})

            combined_result.append({
                "station": station_cn,
                "temperature": temp_str,
                "humidity": humid_str,
                "time": time_val,
                "lat": lat,
                "lng": lng,
                "t_raw": t_val,
                "h_raw": h_val
            })

        # 統計數據計算
        avg_humid = sum(humidities) / len(humidities) if humidities else 0
        count_90 = sum(1 for h in humidities if h >= 90)
        count_95 = sum(1 for h in humidities if h >= 95)
        total_stations = len(humidities)

        # 雲海條件評估
        cloud_sea_status = "條件未成熟"
        if avg_humid >= 95 or count_95 >= 3:
            cloud_sea_status = "極佳！全港高度潮濕，極利於觀賞雲海"
        elif avg_humid >= 90 or count_90 >= 5:
            cloud_sea_status = "良好，部分高地或山區有望出現雲海"

        # 逆溫層與輻射冷卻分析提示
        analysis_notes = []
        if temperatures:
            min_temp = min(temperatures)
            max_temp = max(temperatures)
            if (max_temp - min_temp) > 5.0:
                analysis_notes.append("日夜溫差或站點溫差較大，內陸輻射冷卻效應顯著。")
        
        rc_active = [s for s in radiation_cooling_stations if s['temp'] < 18] # 假設低溫時輻射冷卻明顯
        if radiation_cooling_stations:
            analysis_notes.append(f"已偵測內陸輻射冷卻監測站（如打鼓嶺/石崗等），當前低溫表現正常。")

        return jsonify({
            "stations": combined_result,
            "stats": {
                "avg_humidity": round(avg_humid, 1),
                "count_90": count_90,
                "count_95": count_95,
                "total": total_stations,
                "cloud_sea_status": cloud_sea_status,
                "analysis_notes": analysis_notes
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
