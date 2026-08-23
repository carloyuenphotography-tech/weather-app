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

    # 優先抓取繁體中文站名
    station_name_tc = props.get('AutomaticWeatherStation_tc') or props.get('AutomaticWeatherStation_en') or props.get('name') or '未知站點'
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

    return station_name_tc, {
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
        temp_data = fetch_station_data(TEMP_ZIP_URL, 'temp')
        humid_data = fetch_station_data(HUMIDITY_ZIP_URL, 'humidity')

        all_stations = set(list(temp_data.keys()) + list(humid_data.keys()))
        
        combined_result = []
        humidities = []
        
        # 用於逆溫層與輻射冷卻分析的資料收集
        high_alt_temps = {}
        low_alt_temps = {}
        radiation_cooling_stations = []
        
        high_stations = ["大帽山", "大老山", "Tai Mo Shan", "Tate's Cairn"]
        cooling_targets = ["打鼓嶺", "石崗", "濕地公園", "西貢", "Ta Kwu Ling", "Shek Kong", "Wetland Park", "Sai Kung"]

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

            # 分類高地與低地氣溫，用於逆溫層計算
            if any(hs in station for hs in high_stations):
                if t_val is not None:
                    high_alt_temps[station] = t_val
            else:
                if t_val is not None:
                    low_alt_temps[station] = t_val

            # 輻射冷卻檢測
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

        # 雲海統計
        avg_humid = sum(humidities) / len(humidities) if humidities else 0
        count_90 = sum(1 for h in humidities if h >= 90)
        count_95 = sum(1 for h in humidities if h >= 95)

        cloud_sea_status = "條件未成熟"
        if avg_humid >= 95 or count_95 >= 3:
            cloud_sea_status = "極佳！全港高度潮濕，極利於觀賞雲海"
        elif avg_humid >= 90 or count_90 >= 5:
            cloud_sea_status = "良好，部分山區有望出現雲海"

        # 逆溫層（Inversion Layer）判斷邏輯
        inversion_status = "未探測到顯著逆溫"
        if high_alt_temps and low_alt_temps:
            avg_low_temp = sum(low_alt_temps.values()) / len(low_alt_temps)
            max_high_temp = max(high_alt_temps.values())
            # 若高地溫度接近甚至高於平地平均溫，代表出現逆溫
            if max_high_temp >= (avg_low_temp - 1.5):
                inversion_status = "⚠️ 探測到逆溫現象（高地氣溫異常偏高/與平地相若）"

        # 輻射冷卻判斷
        rc_status = "未明顯出現"
        if radiation_cooling_stations:
            min_rc_temp = min([s['temp'] for s in radiation_cooling_stations])
            rc_status = f"內陸站點（如打鼓嶺/石崗等）最低錄得 {min_rc_temp}°C，輻射冷卻作用運作中"

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
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
