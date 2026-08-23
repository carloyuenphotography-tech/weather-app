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
WIND_ZIP_URL = "https://static.csdi.gov.hk/csdi-webpage/download/9ec8faca33f750339941f5f01689f654/geojson"

# 🎯 站名中英文對照表
STATION_NAME_MAP = {
    "HK Observatory": "香港天文台",
    "Tai Mo Shan": "大帽山",
    "Tate's Cairn": "大老山",
    "Ta Kwu Ling": "打鼓嶺",
    "Shek Kong": "石崗",
    "Sai Kung": "西貢",
    "Wetland Park": "濕地公園",
    "Sha Tin": "沙田",
    "Tuen Mun": "屯門",
    "Chek Lap Kok": "赤鱲角",
    "Cheung Chau": "長洲",
    "Tseung Kwan O": "將軍澳",
    "Kowloon City": "九龍城",
    "Waglan Island": "橫瀾島",
    "Kau Sai Chau": "滘西洲",
    "King's Park": "京士柏",
    "Lau Fau Shan": "流浮山",
    "Pak Tam Chung": "北潭湧",
    "Peng Chau": "坪洲",
    "Shau Kei Wan": "筲箕灣",
    "Sheung Shui": "上水",
    "Tai Po": "大埔",
    "Tai Lung": "大龍",
    "Clear Water Bay": "清水灣",
    "Hong Kong Park": "香港公園",
    "Kai Tak Runway Park": "啟德跑道公園",
    "Wong Tai Sin": "黃大仙",
    "Kwun Tong": "觀塘",
    "Sham Shui Po": "深水埗",
    "Tsuen Wan Ho Koon": "荃灣可觀",
    "Tsuen Wan Shing Mun": "城門谷",
    "Tsuen Wan": "荃灣",
    "Wong Chuk Hang": "黃竹坑"
}

def get_tc_name(en_name):
    if not en_name: return "未知站點"
    en_lower = en_name.lower()
    for eng_key, tc_val in STATION_NAME_MAP.items():
        if eng_key.lower() in en_lower:
            return tc_val
    return en_name

def fetch_single_station(feature, val_type):
    try:
        props = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        coords = geometry.get('coordinates', [])
        
        lng = coords[0] if len(coords) > 0 else None
        lat = coords[1] if len(coords) > 1 else None

        en_name = props.get('AutomaticWeatherStation_en') or props.get('STATION_NAME') or props.get('name') or ''
        matched_name = get_tc_name(en_name)

        data_url = props.get('Data_url')
        val_str = None
        wind_dir = ""
        max_gust = ""
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
                                try: val_str = float(val)
                                except: pass
                            elif val_type == 'humidity' and ('humidity' in k_lower or 'rh' in k_lower) and val:
                                try: val_str = float(val)
                                except: pass
                            elif val_type == 'wind':
                                if ('dir' in k_lower or 'direction' in k_lower) and val:
                                    wind_dir = val
                                elif ('gust' in k_lower or 'maximum' in k_lower) and val:
                                    max_gust = val
                            if ('time' in k_lower or 'date' in k_lower) and val:
                                timestamp = val
            except Exception:
                pass

        if val_type == 'wind':
            return matched_name, {
                "wind_direction": wind_dir,
                "max_gust": max_gust,
                "time": timestamp,
                "lat": lat,
                "lng": lng
            }
        else:
            return matched_name, {
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
        if response.status_code != 200: return data_map

        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            file_list = z.namelist()
            target_file = next((f for f in file_list if f.endswith('.json') or f.endswith('.geojson')), None)
            if not target_file: return data_map

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
                        except: pass
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
        wind_data = fetch_station_data(WIND_ZIP_URL, 'wind')

        all_stations = set(list(temp_data.keys()) + list(humid_data.keys()) + list(wind_data.keys()))
        
        combined_result = []
        humidities = []
        station_humid_list = []
        station_temps = {}
        hko_temp = None

        for station in all_stations:
            t_info = temp_data.get(station, {})
            h_info = humid_data.get(station, {})
            w_info = wind_data.get(station, {})

            lat = t_info.get('lat') or h_info.get('lat') or w_info.get('lat')
            lng = t_info.get('lng') or h_info.get('lng') or w_info.get('lng')
            time_val = t_info.get('time') or h_info.get('time') or w_info.get('time') or '即時'

            t_val = t_info.get('value')
            h_val = h_info.get('value')
            w_dir = w_info.get('wind_direction', '')
            m_gust = w_info.get('max_gust', '')

            temp_str = f"{t_val}°C" if t_val is not None else ""
            humid_str = f"{h_val}%" if h_val is not None else ""
            gust_str = f"{m_gust} km/h" if m_gust else ""

            if h_val is not None:
                humidities.append(h_val)
                station_humid_list.append({"station": station, "humidity": h_val})

            if t_val is not None:
                station_temps[station] = t_val
                if station == "香港天文台":
                    hko_temp = t_val

            combined_result.append({
                "station": station,
                "temperature": temp_str,
                "humidity": humid_str,
                "wind_direction": w_dir,
                "max_gust": gust_str,
                "time": time_val,
                "lat": lat,
                "lng": lng
            })

        avg_humid = sum(humidities) / len(humidities) if humidities else 0
        count_95 = sum(1 for h in humidities if h >= 95)
        count_90 = sum(1 for h in humidities if h >= 90)

        station_humid_list.sort(key=lambda x: x["humidity"], reverse=True)
        top_5_humid = station_humid_list[:5]

        cloud_sea_status = "條件未成熟"
        if avg_humid >= 95 or count_95 >= 2:
            cloud_sea_status = "極佳！全港高度潮濕，極利於觀賞雲海"
        elif avg_humid >= 90 or count_90 >= 3:
            cloud_sea_status = "良好，部分山區有望出現雲海"

        baseline_temp = hko_temp if hko_temp is not None else (sum(station_temps.values()) / len(station_temps) if station_temps else 20)

        tai_mo_shan_temp = station_temps.get("大帽山")
        tate_cairn_temp = station_temps.get("大老山")

        tms_diff_str = ""
        tc_diff_str = ""
        inversion_detected = False

        if tai_mo_shan_temp is not None:
            diff_tms = round(tai_mo_shan_temp - baseline_temp, 1)
            tms_diff_str = f"{diff_tms:+.1f}°C"
            if diff_tms > -3.0: inversion_detected = True

        if tate_cairn_temp is not None:
            diff_tc = round(tate_cairn_temp - baseline_temp, 1)
            tc_diff_str = f"{diff_tc:+.1f}°C"
            if diff_tc > -2.5: inversion_detected = True

        inversion_status = "⚠️ 探測到逆溫現象（高地氣溫異常偏高）" if inversion_detected else "正常垂直遞減（未見逆溫）"

        rc_status = "未明顯出現"
        inland_stations = ["打鼓嶺", "石崗"]
        inland_temps = [val for name, val in station_temps.items() if name in inland_stations]
        
        if inland_temps and hko_temp is not None:
            min_inland = min(inland_temps)
            rc_diff = round(hko_temp - min_inland, 1)
            if rc_diff >= 2.0:
                rc_status = f"顯著！內陸比市區低 {rc_diff}°C（輻射冷卻）"
            else:
                rc_status = f"微弱（溫差 {rc_diff}°C）"

        return jsonify({
            "stations": combined_result,
            "stats": {
                "avg_humidity": round(avg_humid, 1),
                "count_95": count_95,
                "cloud_sea_status": cloud_sea_status,
                "top_humid_stations": top_5_humid,
                "tms_diff": tms_diff_str,
                "tc_diff": tc_diff_str,
                "inversion_status": inversion_status,
                "radiation_cooling": rc_status
            }
        })
    except Exception as e:
        return jsonify({"stations": [], "stats": {}, "error": str(e)}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
