from datetime import datetime, timedelta, timezone
import os
from flask import Flask, jsonify
from flask_cors import CORS
import requests
import xarray as xr

app = Flask(__name__)
CORS(app)  # 允許你的 GitHub Pages 網頁跨域呼叫

cached_data = {
    "timestamp": None,
    "k_value": None,
    "celsius": None,
    "status": "Initializing",
}
last_fetch_time = None


@app.route("/api/satellite-k", methods=["GET"])
def get_satellite_k():
    global cached_data, last_fetch_time
    now = datetime.now(timezone.utc)

    # 快取機制：10 分鐘內重複請求直接回傳，保護伺服器與 S3 頻寬
    if last_fetch_time and (now - last_fetch_time).total_seconds() < 600:
        return jsonify(cached_data)

    # 尋找 NOAA AWS S3 最新檔案 (從 30 分鐘前開始找)
    now_utc = now - timedelta(minutes=30)
    file_downloaded = False
    local_file = "temp_himawari.nc"
    target_str = ""

    for i in range(6):
        test_time = now_utc - timedelta(minutes=10 * i)
        rounded_minute = (test_time.minute // 10) * 10
        target_time = test_time.replace(
            minute=rounded_minute, second=0, microsecond=0
        )

        year, month, day, hour, minute = (
            target_time.strftime("%Y"),
            target_time.strftime("%m"),
            target_time.strftime("%d"),
            target_time.strftime("%H"),
            target_time.strftime("%M"),
        )
        file_name = (
            f"{year}{month}{day}{hour}{minute}00-AHI-H09-FLDK-Band13-NC020.nc"
        )
        url = f"https://noaa-himawari9.s3.amazonaws.com/AHI-L1b-FLDK/{year}/{month}/{day}/{hour}{minute}/{file_name}"

        res = requests.get(url, stream=True)
        if res.status_code == 200:
            with open(local_file, "wb") as f:
                for chunk in res.iter_content(chunk_size=8192):
                    f.write(chunk)
            file_downloaded = True
            target_str = f"{year}-{month}-{day} {hour}:{minute} UTC"
            break

    if not file_downloaded:
        return jsonify(
            {"error": "Satellite data not yet available on AWS"}
        ), 504

    try:
        # 解析 NetCDF 檔案並提取香港座標 (北緯 22.3193, 東經 114.1694)
        ds = xr.open_dataset(local_file)
        tbb_hk = ds["tbb"].sel(
            latitude=22.3193, longitude=114.1694, method="nearest"
        ).values
        k_val = float(tbb_hk)

        cached_data = {
            "timestamp": target_str,
            "k_value": round(k_val, 2),
            "celsius": round(k_val - 273.15, 2),
            "status": "Success",
        }
        last_fetch_time = now
        ds.close()

        if os.path.exists(local_file):
            os.remove(local_file)

        return jsonify(cached_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)