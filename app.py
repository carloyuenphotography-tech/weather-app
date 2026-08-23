import io
import zipfile
import requests
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允許任何網頁來讀取這個 API（解決 CORS 問題）

# 您提供的 CSDI 靜態下載連結
CSDI_ZIP_URL = "https://static.csdi.gov.hk/csdi-webpage/download/04db0982a43f561db9e922cd082b09f9/geojson"

@app.route('/humidity', methods=['GET'])
def get_humidity():
    try:
        # 1. 下載 ZIP 檔案
        response = requests.get(CSDI_ZIP_URL)
        if response.status_code != 200:
            return jsonify({"error": "無法從 CSDI 下載資料"}), 500

        # 2. 在記憶體中解壓縮
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            # 尋找壓縮檔裡面的 .json 或 .geojson 檔案
            file_list = z.namelist()
            target_file = next((f for f in file_list if f.endswith('.json') or f.endswith('.geojson')), None)
            
            if not target_file:
                return jsonify({"error": "壓縮檔內找不到 geojson 檔案"}), 404

            # 3. 讀取內容並轉為 JSON
            with z.open(target_file) as f:
                import json
                geo_data = json.loads(f.read().decode('utf-8'))
                return jsonify(geo_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)