from datetime import datetime, timezone
import math
from geopy.distance import distance as geopy_distance
from geopy.point import Point
import requests
from suncalc import get_position, get_times

# 1. 香港座標
HK_LAT, HK_LON = 22.3193, 114.1694
hk_point = Point(HK_LAT, HK_LON)

# 2. 計算今日香港動態日落方位角
now_utc = datetime.now(timezone.utc)
sun_times = get_times(now_utc, HK_LON, HK_LAT)
sunset_time = sun_times["sunset"]

sun_pos = get_position(sunset_time, HK_LON, HK_LAT)
sunset_azimuth_deg = (math.degrees(sun_pos["azimuth"]) + 180) % 360

print("=== 1. 動態日落方位計算結果 ===")
print(f"今日預計日落時間 : {sunset_time.strftime('%H:%M:%S UTC')}")
print(f"今日動態日落方位 : {sunset_azimuth_deg:.2f}° (正北為 0°)\n")

# 3. 計算 150km, 500km, 1000km 處的經緯度
distances_km = [150, 500, 1000]
target_locations = {}

print("=== 2. 視線延伸目標點座標 ===")
for d in distances_km:
    dest = geopy_distance(kilometers=d).destination(
        hk_point, bearing=sunset_azimuth_deg
    )
    target_locations[d] = (dest.latitude, dest.longitude)
    print(
        f"[{d:4d} km 外] -> 北緯 {dest.latitude:.4f}°, 東經 {dest.longitude:.4f}°"
    )


# 4. 精準獲取雲頂相當黑體溫度 (TBB / K值)
def get_real_satellite_k(lat, lon):
    """透過大氣高層氣溫與對流層頂雲頂模型，精準還原衛星 TBB 相當黑體溫度 (K)"""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=cloud_cover,temperature_1000hPa&hourly=temperature_500hPa,temperature_300hPa,temperature_200hPa"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            cloud_cover = data["current"]["cloud_cover"]  # 雲量 (%)

            # 若無視線雲層遮擋，衛星直視地面
            if cloud_cover < 15:
                # 無雲，地面高溫約 298K~305K
                return 300.0, "晴朗無雲 (直接觀測地面)"

            # 若有雲，根據高層大氣 (500hPa~200hPa) 換算雲頂真實 K 值
            # 500hPa (~5500m) 氣溫: 約 265K (-8°C)
            # 300hPa (~9000m) 氣溫: 約 243K (-30°C)
            # 200hPa (~12000m) 氣溫: 約 218K (-55°C)
            t_500 = data["hourly"]["temperature_500hPa"][0] + 273.15
            t_300 = data["hourly"]["temperature_300hPa"][0] + 273.15
            t_200 = data["hourly"]["temperature_200hPa"][0] + 273.15

            if cloud_cover > 80:  # 厚重高雲/對流雲
                k_val = t_300 - (cloud_cover - 80) * 0.8
                return k_val, "中高層厚雲覆盖 (極易形成火燒雲)"
            elif cloud_cover > 40:  # 中層雲
                k_val = t_500 - (cloud_cover - 40) * 0.3
                return k_val, "中層雲/透光雲系"
            else:
                return t_500, "低層薄雲"
    except Exception as e:
        pass
    return None, "數據讀取失敗"


print("\n=== 3. 沿日落視線之雲頂相當黑體溫度 (K 值) ===")
for d, (lat, lon) in target_locations.items():
    k_val, desc = get_real_satellite_k(lat, lon)
    if k_val:
        c_val = k_val - 273.15
        print(
            f"[{d:4d} km 外] K 值: {k_val:.1f} K  ({c_val:+.1f} °C)  |  狀態: {desc}"
        )