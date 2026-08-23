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

# 🎯 精選核心氣象站清單（專注於高地逆溫、內陸輻射冷卻與主要市區代表）
TARGET_STATIONS = [
    "香港天文台", "HK Observatory",
    "大帽山", "Tai Mo Shan",
    "大老山", "Tate's Cairn",
    "打鼓嶺", "Ta Kwu Ling",
    "石崗", "Shek Kong",
    "西貢", "Sai Kung",
    "濕地公園", "Wetland Park",
    "沙田", "Sha Tin",
    "屯門", "Tuen Mun",
    "赤鱲角", "Chek Lap Kok",
    "長洲", "Cheung Chau",
    "將軍澳", "Tseung Kwan O",
    "九龍城", "Kowloon City",
    "橫瀾島", "Walang Island",
    "滘西洲", "Kau Sai Chau"
]

def fetch_single_station(feature, val_type):
    try:
        props = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        coords = geometry.get('coordinates', [])
        
        lng = coords[0] if len(coords) > 0 else None
        lat = coords[1] if len(coords) > 1 else None

        station_name_tc = props.get('AutomaticWeatherStation_tc') or ''
        station_name_en = props.get('AutomaticWeatherStation_en') or ''
        station_name = station_name_tc or station_name_en or '未知站點'

        # 篩選機制：如果不在精選清單內，直接略過，不發送 CSV 請求！
        is_target = any(target.lower() in station_name.lower() for target in TARGET_STATIONS)
        if not is_target:
            return None, None

        data_url = props.get('Data_url')
        val_str = None
        timestamp = "即時"

        if data_url:
            try:
                csv_res = requests.get(data_url, timeout=2)
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

        return station_name_tc or station_name_en, {
            "value": val_str,
            "time": timestamp,
            "lat": lat,
            "lng": lng
        }
    except Exception:
        return None, None

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
                        try:
                            s_name, s_info = future.result()
                            if s_name and s_info:
                                data_map[s_name] = s_info
                        except:
                            pass
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
        high_alt_temps = {}
        low_alt_temps = {}
        radiation_cooling_stations = []
        
        high_stations = ["大帽山", "大老山"]
        cooling_targets = ["打鼓嶺", "石崗", "濕地公園", "西貢"]

        for station in all_stations:
            t_info = temp_data.get(station, {})
            h_info = humid_data.get(station, {})

            lat = t_info.get('lat') or h_info.get('lat')
            lng = t_info.get('lng') or h_info.get('lng')
            time_val = t_info.get('time') or h_info.get('time') or '即時'

            t_val = t_info.get('value')
            h_val = h_info.get('value')

            temp_str = f"{t_val}°C" if t_val is not None else "資料未明"
            humid_str = f"{h_val}%" if h_val is not None else "資料未明"

            if h_val is not None:
                humidities.append(h_val)

            if any(hs in station for hs in high_stations):
                if t_val is not None:
                    high_alt_temps[station] = t_val
            else:
                if t_val is not None:
                    low_alt_temps[station] = t_val

            if any(ct in station for ct in cooling_targets):
                if t_val is not None:
                    radiation_cooling_stations.append({"station": station, "temp": t_val})

            combined_result.append({
                "station": station,
                "temperature": temp_str,
                "humidity": humid_str,
                "time": time_val,
                "lat": lat,
                "lng": lng
            })

        avg_humid = sum(humidities) / len(humidities) if humidities else 0
        count_95 = sum(1 for h in humidities if h >= 95)

        cloud_sea_status = "條件未成熟"
        if avg_humid >= 95 or count_95 >= 2:
            cloud_sea_status = "極佳！全港高度潮濕，極利於觀賞雲海"
        elif avg_humid >= 90 or sum(1 for h in humidities if h >= 90) >= 3:
            cloud_sea_status = "良好，部分山區有望出現雲海"

        inversion_status = "未探測到顯著逆溫"
        if high_alt_temps and low_alt_temps:
            avg_low_temp = sum(low_alt_temps.values()) / len(low_alt_temps)
            max_high_temp = max(high_alt_temps.values())
            if max_high_temp >= (avg_low_temp - 1.5):
                inversion_status = "⚠️ 探測到逆溫現象（高地氣溫異常偏高）"

        rc_status = "未明顯出現"
        if radiation_cooling_stations:
            min_rc_temp = min([s['temp'] for s in radiation_cooling_stations])
            rc_status = f"內陸站點最低錄得 {min_rc_temp}°C，輻射冷卻運作中"

        return jsonify({
            "stations": combined_result,
            "stats": {
                "avg_humidity": round(avg_humid, 1),
                "count_95": count_95,
                "cloud_sea_status": cloud_sea_status,
                "inversion_status": inversion_status,
                "radiation_cooling": rc_status
            }
        })
    except Exception as e:
        return jsonify({
            "stations": [],
            "stats": {
                "avg_humidity": 0,
                "count_95": 0,
                "cloud_sea_status": "讀取錯誤",
                "inversion_status": "讀取錯誤",
                "radiation_cooling": "讀取錯誤"
            },
            "error": str(e)
        }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
