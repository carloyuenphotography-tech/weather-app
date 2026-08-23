function toggleDrawer() {
    const drawer = document.getElementById('drawerMenu');
    const overlay = document.getElementById('drawerOverlay');
    drawer.classList.toggle('active');
    overlay.classList.toggle('active');
}

let userSunMode = 'auto';
let userMoonMode = 'auto';
let lunarCalendarData = {}; // 儲存 CSV 農曆對應表

function setSunDisplayMode(mode) { userSunMode = mode; updateAstronomicalData(); }
function setMoonDisplayMode(mode) { userMoonMode = mode; updateAstronomicalData(); }

function formatCountdown(diffMs) {
    const absMs = Math.abs(diffMs);
    const totalMins = Math.floor(absMs / (1000 * 60));
    const hours = Math.floor(totalMins / 60);
    const mins = totalMins % 60;
    let timeStr = hours > 0 ? `${hours}小時${mins}分` : `${mins}分鐘`;
    return diffMs > 0 ? `還有 ${timeStr}` : `已過 ${timeStr}`;
}

// 自動根據當前年份載入對應的農曆 CSV 檔案 (同時支援 nongli_calendar/ 子資料夾及根目錄)
async function loadLunarCalendarData() {
    const now = new Date();
    const year = now.getFullYear();
    const paths = [
        `nongli_calendar/nongli_calendar_${year}.csv`,
        `nongli_calendar_${year}.csv`
    ];

    let loaded = false;
    for (let path of paths) {
        try {
            const response = await fetch(path);
            if (response.ok) {
                const text = await response.text();
                parseLunarCSV(text);
                loaded = true;
                break;
            }
        } catch (err) {
            // 嘗試下一個路徑
        }
    }

    if (!loaded) {
        console.warn(`無法載入 ${year} 年農曆 CSV 檔案，將使用內置計算作為備份`);
    }
    updateAstronomicalData();
}

// 解析 CSV 內容並轉換日期格式 (例如 23-Aug-26 -> 2026-08-23)
function parseLunarCSV(text) {
    const lines = text.split(/\r\n|\n/);
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        if (!line) continue;
        let parts = line.split(',');
        if (parts.length >= 5) {
            let rawDate = parts[0].trim().replace(/["']/g, '');
            let lunarMonth = parts[3].trim().replace(/["']/g, '');
            let lunarDate = parts[4].trim().replace(/["']/g, '');
            
            let stdDateKey = parseCSVDateToYYYYMMDD(rawDate);
            if (stdDateKey) {
                lunarCalendarData[stdDateKey] = `${lunarMonth}${lunarDate}`;
            }
        }
    }
}

// 轉換 CSV 中的日期格式 (例如 23-Aug-26) 為 YYYY-MM-DD
function parseCSVDateToYYYYMMDD(dateStr) {
    const parts = dateStr.split('-');
    if (parts.length === 3) {
        let day = parts[0].padStart(2, '0');
        let monthStr = parts[1];
        let yearPart = parts[2];
        let fullYear = yearPart.length === 2 ? '20' + yearPart : yearPart;
        
        const months = {
            'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
            'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
            'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
        };
        let month = months[monthStr] || '01';
        return `${fullYear}-${month}-${day}`;
    }
    return null;
}

function getLunarDateString(date) {
    if (!date || isNaN(date)) return "--";
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    const key = `${yyyy}-${mm}-${dd}`;

    // 優先從載入的 CSV 資料中尋找對應農曆
    if (lunarCalendarData[key]) {
        return lunarCalendarData[key];
    }

    // 若 CSV 內無此日期，則採用原本的演算法作為備份
    const baseDate = new Date(2026, 1, 17);
    const diffDays = Math.floor((date - baseDate) / (1000 * 60 * 60 * 24));
    const synodicMonth = 29.53059;
    let lunarDayVal = (diffDays % synodicMonth + synodicMonth) % synodicMonth;
    let monthIndex = Math.floor(diffDays / synodicMonth);
    let lunarMonth = 1 + (monthIndex % 12);
    if (lunarMonth <= 0) lunarMonth += 12;
    let lunarDay = Math.floor(lunarDayVal) + 1;
    if (lunarDay > 30) lunarDay = 30;

    const monthNames = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "臘"];
    const dayNames = ["初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
                      "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
                      "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十"];
    return `${monthNames[lunarMonth - 1] || "六"}月${dayNames[lunarDay - 1] || "廿三"}`;
}

function getAzimuthDirection(deg) {
    const val = (deg + 360) % 360;
    if (val >= 337.5 || val < 22.5) return "北";
    if (val >= 22.5 && val < 67.5) return "東北";
    if (val >= 67.5 && val < 112.5) return "東";
    if (val >= 112.5 && val < 157.5) return "東南";
    if (val >= 157.5 && val < 202.5) return "南";
    if (val >= 202.5 && val < 247.5) return "西南";
    if (val >= 247.5 && val < 292.5) return "西";
    if (val >= 292.5 && val < 337.5) return "西北";
    return "北";
}

function initAqiMap() {
    const TOKEN = '430276c460fd69058de6f20acf54c04dbc3a1d96'; 
    const aqiMap = L.map('aqi-map').setView([22.3193, 114.1694], 11);

    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    }).addTo(aqiMap);

    const waqiTileUrl = `https://tiles.waqi.info/tiles/usepa-aqi/{z}/{x}/{y}.png?token=${TOKEN}`;
    L.tileLayer(waqiTileUrl, {
        attribution: 'Air Quality Tile &copy; <a href="https://waqi.info">WAQI</a>',
        maxZoom: 18
    }).addTo(aqiMap);
}

// 讀取天文台天氣警告概要 (warnsum API)
async function fetchWeatherWarnings() {
    const container = document.getElementById('warning-summary-container');
    const timeEl = document.getElementById('warning-update-time');
    try {
        const res = await fetch('https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=warnsum&lang=tc');
        if (!res.ok) throw new Error('網絡請求失敗');
        const data = await res.json();
        
        let activeWarnings = [];
        // HKO warnsum JSON 格式通常為物件，各個 key 代表警告代碼，內含 details 或 info
        for (let key in data) {
            if (data.hasOwnProperty(key)) {
                let warnObj = data[key];
                // 若包含 name 或 屬於生效中狀態
                if (warnObj && (warnObj.name || warnObj.actionCode)) {
                    let name = warnObj.name || key;
                    activeWarnings.push(name);
                }
            }
        }

        if (activeWarnings.length > 0) {
            container.style.justifyContent = 'flex-start';
            container.style.textAlign = 'left';
            container.innerHTML = `<div style="color: #e11d48; font-weight: bold; margin-bottom: 6px;">⚠️ 現時生效天氣警告：</div>` +
                                  `<ul style="margin: 0; padding-left: 20px;">` +
                                  activeWarnings.map(w => `<li>${w}</li>`).join('') +
                                  `</ul>`;
        } else {
            container.style.justifyContent = 'center';
            container.style.textAlign = 'center';
            container.innerHTML = `<span style="color: #166534; font-weight: bold;">🟢 目前沒有生效的天氣警告</span>`;
        }
        timeEl.innerHTML = `💡 天氣警告狀態更新正常`;
    } catch (err) {
        container.style.justifyContent = 'center';
        container.style.textAlign = 'center';
        container.innerHTML = `<span style="color: #991b1b;">無法載入天氣警告資料</span>`;
    }
}

async function fetchNineDayForecast() {
    const container = document.getElementById('fnd-container');
    const generalEl = document.getElementById('fnd-general-situation');
    const timeEl = document.getElementById('fnd-update-time');
    try {
        const res = await fetch('https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=fnd&lang=tc');
        const data = await res.json();
        if (data) {
            generalEl.innerText = data.generalSituation || "暫無天氣概況";
            if (data.updateTime) {
                timeEl.innerText = `發布時間: ${data.updateTime.replace('T', ' ').substring(0, 16)}`;
            }
            const records = data.weatherForecast;
            if (records && Array.isArray(records)) {
                if (records.length > 0) {
                    let todayMin = records[0].forecastMintemp ? `${records[0].forecastMintemp.value}°C` : '--°C';
                    let todayMax = records[0].forecastMaxtemp ? `${records[0].forecastMaxtemp.value}°C` : '--°C';
                    const minMaxEl = document.getElementById('summary-minmax-temp');
                    if (minMaxEl) {
                        minMaxEl.innerText = `↓ ${todayMin} ↑ ${todayMax}`;
                    }
                }

                container.innerHTML = '';
                records.forEach(day => {
                    let dStr = day.forecastDate;
                    let formattedDate = `${dStr.substring(4, 6)}/${dStr.substring(6, 8)}`;
                    let minTemp = day.forecastMintemp ? `${day.forecastMintemp.value}°C` : '--';
                    let maxTemp = day.forecastMaxtemp ? `${day.forecastMaxtemp.value}°C` : '--';
                    let minRh = day.forecastMinrh ? `${day.forecastMinrh.value}%` : '';
                    let maxRh = day.forecastMaxrh ? `${day.forecastMaxrh.value}%` : '';
                    let humStr = (minRh && maxRh) ? `濕度: ${minRh}-${maxRh}` : '';

                    container.innerHTML += `
                        <div class="fnd-box">
                            <div>
                                <div class="fnd-date">${formattedDate} (${day.week})</div>
                                <div style="font-size: 0.8rem; color: #0284c7; font-weight: bold; margin-bottom: 2px;">${day.forecastWeather}</div>
                            </div>
                            <div>
                                <div class="fnd-temp">${minTemp} - ${maxTemp}</div>
                                <div class="fnd-hum">${humStr}</div>
                            </div>
                        </div>
                    `;
                });
            }
        }
    } catch (err) {
        container.innerHTML = `<p style="color:red;">九天天氣預報載入失敗。</p>`;
    }
}

async function fetchTideData() {
    const container = document.getElementById('tide-container');
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const dd = String(now.getDate()).padStart(2, '0');
    const todayKey = `${yyyy}-${mm}-${dd}`;

    const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000);
    const tomorrowKey = `${tomorrow.getFullYear()}-${String(tomorrow.getMonth() + 1).padStart(2, '0')}-${String(tomorrow.getDate()).padStart(2, '0')}`;

    try {
        const res = await fetch('tide_30days.json');
        if (!res.ok) throw new Error();
        const tideMap = await res.json();
        container.innerHTML = '';

        function renderDayTides(records) {
            if (!records || records.length === 0) return `<p style="font-size: 0.9rem; color: #64748b; text-align: center; margin: 4px 0;">暫無紀錄</p>`;
            let html = '';
            
            for (let i = 0; i < records.length; i++) {
                let current = records[i];
                let curHeight = parseFloat(current.height);
                let tideType = "漲潮 📈";
                let typeClass = "tide-type-up";

                let prevHeight = i > 0 ? parseFloat(records[i-1].height) : null;
                let nextHeight = i < records.length - 1 ? parseFloat(records[i+1].height) : null;

                if (prevHeight !== null && nextHeight !== null) {
                    if (curHeight < prevHeight && curHeight < nextHeight) {
                        tideType = "低潮🔽"; typeClass = "tide-type-down";
                    } else if (curHeight > prevHeight && curHeight > nextHeight) {
                        tideType = "高潮🔼"; typeClass = "tide-type-up";
                    } else if (curHeight > prevHeight) {
                        tideType = "漲潮 📈"; typeClass = "tide-type-up";
                    } else {
                        tideType = "退潮 📉"; typeClass = "tide-type-down";
                    }
                } else if (prevHeight !== null) {
                    tideType = curHeight > prevHeight ? "漲潮 📈" : "退潮 📉";
                    typeClass = curHeight > prevHeight ? "tide-type-up" : "tide-type-down";
                } else if (nextHeight !== null) {
                    tideType = nextHeight > curHeight ? "漲潮 📈" : "退潮 📉";
                    typeClass = nextHeight > curHeight ? "tide-type-up" : "tide-type-down";
                }

                html += `<div class="tide-row"><span class="${typeClass}"><strong>${tideType}</strong></span><span>🌊 ${current.height} m</span><span>⏰ <strong>${current.time}</strong></span></div>`;
            }
            return html;
        }

        container.innerHTML = `<div class="tide-section-title">📅 今日 (${todayKey})</div>` + renderDayTides(tideMap[todayKey]) +
                              `<div class="tide-section-title">📅 明日 (${tomorrowKey})</div>` + renderDayTides(tideMap[tomorrowKey]);
    } catch (err) {
        container.innerHTML = `<p style="text-align: center; color: red;">無法載入 tide_30days.json</p>`;
    }
}

async function fetchHKOWeatherData() {
    try {
        const flwRes = await fetch('https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=flw&lang=tc');
        if (flwRes.ok) {
            const flw = await flwRes.json();
            document.getElementById('flw-general').innerText = flw.generalSituation || "--";
            document.getElementById('flw-desc').innerText = flw.forecastDesc || "--";
            document.getElementById('flw-outlook').innerText = flw.outlook || "--";

            if (flw.updateTime) {
                let formattedTime = flw.updateTime.replace('T', ' ').substring(0, 19);
                document.getElementById('flw-update-time').innerHTML = `💡 預報發布時間：<strong>${formattedTime}</strong>`;
            } else if (flw.forecastPeriod) {
                document.getElementById('flw-update-time').innerHTML = `💡 預報發布時間：<strong>${flw.forecastPeriod}</strong>`;
            } else {
                document.getElementById('flw-update-time').innerHTML = `💡 本港地區天氣預報 (香港天文台)`;
            }

            const warningBox = document.getElementById('summary-warning-box');
            const warningText = document.getElementById('summary-warning-text');
            
            let alertContent = "";
            if (flw.fireWarning) alertContent += `[${flw.fireWarning}] `;
            if (flw.generalSituation) {
                alertContent += flw.generalSituation;
            }

            if (alertContent.trim() !== "") {
                warningText.innerText = alertContent;
                warningBox.style.display = "block";
            } else {
                warningBox.style.display = "none";
            }
        }
    } catch (e) {}

    try {
        const visRes = await fetch('https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=ltmv&rformat=json&lang=tc');
        if (visRes.ok) {
            const visJson = await visRes.json();
            if (visJson && visJson.data) {
                visJson.data.forEach(row => {
                    let station = row[1], valStr = row[2];
                    function updateVis(valId, statId) {
                        document.getElementById(valId).innerText = valStr;
                        const statEl = document.getElementById(statId);
                        
                        if (!valStr || valStr.toUpperCase() === 'N/A') {
                            statEl.innerText = "N/A";
                            statEl.className = "vis-status";
                            return;
                        }

                        let km = parseFloat(valStr);
                        if (valStr.includes('米') && !valStr.includes('公里')) km /= 1000;

                        if (km >= 40) { statEl.innerText = "極佳"; statEl.className = "vis-status status-good"; }
                        else if (km >= 25) { statEl.innerText = "良好"; statEl.className = "vis-status status-normal"; }
                        else if (km >= 1) { statEl.innerText = "一般"; statEl.className = "vis-status status-fair"; }
                        else { statEl.innerText = "霧 / 惡劣"; statEl.className = "vis-status status-poor"; }
                    }
                    if (station.includes('中環')) updateVis('vis-central', 'status-central');
                    if (station.includes('赤鱲角')) updateVis('vis-airport', 'status-airport');
                    if (station.includes('西灣河')) updateVis('vis-swh', 'status-swh');
                    if (station.includes('橫瀾島')) updateVis('vis-wgl', 'status-wgl');
                });
            }
        }
    } catch (e) {}
}

function updateAstronomicalData() {
    const lat = 22.3193;
    const lon = 114.1694;
    const now = new Date();
    const year = now.getFullYear();

    const dateOptions = { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' };
    document.getElementById('current-date-display').innerText = now.toLocaleDateString('zh-HK', dateOptions);

    const sunTimes = SunCalc.getTimes(now, lat, lon);
    const timeOptions = { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Hong_Kong' };

    let sunriseAzimuthDeg = 90;
    let sunsetAzimuthDeg = 270;

    if (sunTimes.sunrise && sunTimes.sunset) {
        document.getElementById('sunrise-time').innerText = sunTimes.sunrise.toLocaleTimeString('zh-HK', timeOptions);
        document.getElementById('sunset-time').innerText = sunTimes.sunset.toLocaleTimeString('zh-HK', timeOptions);

        let targetSunrise = sunTimes.sunrise;
        if (now > targetSunrise) {
            const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000);
            const tomorrowSunTimes = SunCalc.getTimes(tomorrow, lat, lon);
            if (tomorrowSunTimes.sunrise) targetSunrise = tomorrowSunTimes.sunrise;
        }
        document.getElementById('sunrise-countdown').innerText = formatCountdown(targetSunrise - now);
        document.getElementById('sunset-countdown').innerText = formatCountdown(sunTimes.sunset - now);

        const sunrisePos = SunCalc.getPosition(sunTimes.sunrise, lat, lon);
        sunriseAzimuthDeg = (sunrisePos.azimuth * (180 / Math.PI) + 180) % 360;

        const sunsetPos = SunCalc.getPosition(sunTimes.sunset, lat, lon);
        sunsetAzimuthDeg = (sunsetPos.azimuth * (180 / Math.PI) + 180) % 360;
    }

    let isAfterSunriseBeforeSunset = sunTimes.sunrise && sunTimes.sunset && now >= sunTimes.sunrise && now < sunTimes.sunset;
    let activeSunMode = userSunMode === 'auto' ? (isAfterSunriseBeforeSunset ? 'sunset' : 'sunrise') : userSunMode;
    let sunPct = 50;

    if (activeSunMode === 'sunset') {
        document.getElementById('sun-viz-title').innerText = "🧭 日落方位軌跡";
        let sunsetNorm = (sunsetAzimuthDeg - 244.9) / (295.8 - 244.9);
        sunsetNorm = Math.max(0, Math.min(1, sunsetNorm));
        sunPct = 66.7 + (sunsetNorm * 33.3);
        document.getElementById('today-sun-marker').style.left = `${sunPct}%`;
        const sLabel = document.getElementById('today-sun-label');
        sLabel.style.left = `${sunPct}%`;
        sLabel.innerText = `今日日落 ${Math.round(sunsetAzimuthDeg)}° (${getAzimuthDirection(sunsetAzimuthDeg)})`;
    } else {
        document.getElementById('sun-viz-title').innerText = "🧭 日出方位軌跡";
        let sunriseNorm = (sunriseAzimuthDeg - 64.2) / (115.1 - 64.2);
        sunriseNorm = Math.max(0, Math.min(1, sunriseNorm));
        sunPct = sunriseNorm * 33.3;
        document.getElementById('today-sun-marker').style.left = `${sunPct}%`;
        const sLabel = document.getElementById('today-sun-label');
        sLabel.style.left = `${sunPct}%`;
        sLabel.innerText = `今日日出 ${Math.round(sunriseAzimuthDeg)}° (${getAzimuthDirection(sunriseAzimuthDeg)})`;
    }

    const currentSunPos = SunCalc.getPosition(now, lat, lon);
    const currentSunAltDeg = currentSunPos.altitude * (180 / Math.PI);
    const altitudeBanner = document.getElementById('sun-altitude-banner-text');

    if (currentSunAltDeg >= -18.0) {
        altitudeBanner.innerHTML = `☀️ 太陽即時仰角: ${currentSunAltDeg.toFixed(1)}°`;
    } else {
        altitudeBanner.innerHTML = `☀️ 太陽即時仰角: 小於 -18.0° (黑夜)`;
    }

    const terms = [
        { name: "春分", date: new Date(year, 2, 21) },
        { name: "夏至", date: new Date(year, 5, 21) },
        { name: "秋分", date: new Date(year, 8, 23) },
        { name: "冬至", date: new Date(year, 11, 22) }
    ];
    let nextTerm = null;
    for (let term of terms) {
        if (now < term.date) { nextTerm = term; break; }
    }
    if (!nextTerm) nextTerm = { name: "春分", date: new Date(year + 1, 2, 21) };
    const diffDays = Math.ceil((nextTerm.date - now) / (1000 * 60 * 60 * 24));
    document.getElementById('solar-term-text').innerHTML = `🌱 距離下一個重要節氣 <strong>${nextTerm.name}</strong> 還有 <strong>${diffDays}</strong> 天`;

    const moonIllumination = SunCalc.getMoonIllumination(now);
    const moonTimes = SunCalc.getMoonTimes(now, lat, lon);
    const p = moonIllumination.phase;
    const illumPct = Math.round(moonIllumination.fraction * 100);
    document.getElementById('moon-illumination-pct').innerText = `${illumPct}%`;

    let phaseName = "新月";
    if (p < 0.03 || p > 0.97) phaseName = "新月 (朔)";
    else if (p < 0.22) phaseName = "娥眉月";
    else if (p < 0.28) phaseName = "上弦月";
    else if (p < 0.47) phaseName = "盈凸月";
    else if (p < 0.53) phaseName = "滿月 (望)";
    else if (p < 0.72) phaseName = "虧凸月";
    else if (p < 0.78) phaseName = "下弦月";
    else phaseName = "殘月";

    document.getElementById('moon-phase-name').innerText = phaseName;

    const svgMoon = `
        <svg viewBox="0 0 36 36" width="100%" height="100%">
            <circle cx="18" cy="18" r="16" fill="#1e293b" />
            <path d="M18 2 A16 16 0 0 1 18 34 A${Math.abs(16 * (1 - 2 * p))} 16 0 0 ${p < 0.5 ? 1 : 0} 18 2" fill="#f8fafc" />
        </svg>
    `;
    document.getElementById('moon-svg-container').innerHTML = svgMoon;
    document.getElementById('lunar-date-text').innerText = getLunarDateString(now);

    let moonriseAzimuthDeg = 90;
    let moonsetAzimuthDeg = 270;

    if (moonTimes.rise) {
        document.getElementById('moonrise-time').innerText = moonTimes.rise.toLocaleTimeString('zh-HK', timeOptions);
        document.getElementById('moonrise-countdown').innerText = formatCountdown(moonTimes.rise - now);
        const pos = SunCalc.getMoonPosition(moonTimes.rise, lat, lon);
        moonriseAzimuthDeg = (pos.azimuth * (180 / Math.PI) + 180) % 360;
    } else {
        document.getElementById('moonrise-time').innerText = "今日無月出";
        document.getElementById('moonrise-countdown').innerText = "--";
    }

    if (moonTimes.set) {
        document.getElementById('moonset-time').innerText = moonTimes.set.toLocaleTimeString('zh-HK', timeOptions);
        document.getElementById('moonset-countdown').innerText = formatCountdown(moonTimes.set - now);
        const pos = SunCalc.getMoonPosition(moonTimes.set, lat, lon);
        moonsetAzimuthDeg = (pos.azimuth * (180 / Math.PI) + 180) % 360;
    } else {
        document.getElementById('moonset-time').innerText = "今日無月落";
        document.getElementById('moonset-countdown').innerText = "--";
    }

    const currentMoonPos = SunCalc.getMoonPosition(now, lat, lon);
    const currentMoonAltDeg = currentMoonPos.altitude * (180 / Math.PI);
    
    const riseAltEl = document.getElementById('moonrise-alt');
    const setAltEl = document.getElementById('moonset-alt');
    if (riseAltEl) riseAltEl.innerText = `即時仰角: ${currentMoonAltDeg.toFixed(1)}°`;
    if (setAltEl) setAltEl.innerText = `即時仰角: ${currentMoonAltDeg.toFixed(1)}°`;

    let isAfterMoonriseBeforeMoonset = moonTimes.rise && moonTimes.set && moonTimes.rise < moonTimes.set && now >= moonTimes.rise && now < moonTimes.set;
    let activeMoonMode = userMoonMode === 'auto' ? (isAfterMoonriseBeforeMoonset ? 'moonset' : 'moonrise') : userMoonMode;

    if (activeMoonMode === 'moonset') {
        document.getElementById('moon-viz-title').innerText = "🌘 月落方位動態基準";
        let moonSetPct = Math.max(0, Math.min(100, (moonsetAzimuthDeg / 360.0) * 100));
        document.getElementById('today-moon-marker').style.left = `${moonSetPct}%`;
        const mLabel = document.getElementById('today-moon-label');
        mLabel.style.left = `${moonSetPct}%`;
        mLabel.innerText = `今日月落 ${Math.round(moonsetAzimuthDeg)}° (${getAzimuthDirection(moonsetAzimuthDeg)})`;
    } else {
        document.getElementById('moon-viz-title').innerText = "🌕 月出方位動態基準";
        let moonRisePct = Math.max(0, Math.min(100, (moonriseAzimuthDeg / 360.0) * 100));
        document.getElementById('today-moon-marker').style.left = `${moonRisePct}%`;
        const mLabel = document.getElementById('today-moon-label');
        mLabel.style.left = `${moonRisePct}%`;
        mLabel.innerText = `今日月出 ${Math.round(moonriseAzimuthDeg)}° (${getAzimuthDirection(moonriseAzimuthDeg)})`;
    }

    let searchDate = new Date(now.getTime());
    let nextFullMoonDate = null;
    for (let i = 0; i < 30; i++) {
        searchDate.setDate(searchDate.getDate() + 1);
        let info = SunCalc.getMoonIllumination(searchDate);
        if (info.phase >= 0.48 && info.phase <= 0.52) { nextFullMoonDate = new Date(searchDate); break; }
    }
    if (!nextFullMoonDate) nextFullMoonDate = new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000);
    
    const fmRise = SunCalc.getMoonTimes(nextFullMoonDate, lat, lon);
    const fmDateStr = nextFullMoonDate.toLocaleDateString('zh-HK', { month: 'long', day: 'numeric' });
    const fmLunarStr = getLunarDateString(nextFullMoonDate);
    
    let fmRiseStr = "--:--", fmRiseAzStr = "--°", fmRiseDir = "--";
    if (fmRise.rise) {
        fmRiseStr = fmRise.rise.toLocaleTimeString('zh-HK', { hour: '2-digit', minute: '2-digit', hour12: false });
        const pos = SunCalc.getMoonPosition(fmRise.rise, lat, lon);
        let az = (pos.azimuth * (180 / Math.PI) + 180) % 360;
        fmRiseAzStr = `${Math.round(az)}°`; fmRiseDir = getAzimuthDirection(az);
    }

    let fmSetStr = "--:--", fmSetAzStr = "--°", fmSetDir = "--";
    if (fmRise.set) {
        fmSetStr = fmRise.set.toLocaleTimeString('zh-HK', { hour: '2-digit', minute: '2-digit', hour12: false });
        const pos = SunCalc.getMoonPosition(fmRise.set, lat, lon);
        let az = (pos.azimuth * (180 / Math.PI) + 180) % 360;
        fmSetAzStr = `${Math.round(az)}°`; fmSetDir = getAzimuthDirection(az);
    }

    document.getElementById('next-fullmoon-text').innerHTML = 
        `🌕 <strong>下一次滿月</strong>：${fmDateStr} (${fmLunarStr})<br>` +
        `月出: ${fmRiseStr} (${fmRiseAzStr} ${fmRiseDir}) | 月落: ${fmSetStr} (${fmSetAzStr} ${fmSetDir})`;

    fetchHKOWeatherData();
}

const weatherPhotos = [
    { name: "太平山 (望向東面)", img: "https://www.hko.gov.hk/wxinfo/aws/hko_mica/vpa/latest_VPA.jpg", link: "https://www.hko.gov.hk/tc/wxinfo/ts/webcam/VPA_photo.htm" },
    { name: "太平山 (望向東北偏北面)", img: "https://www.hko.gov.hk/wxinfo/aws/hko_mica/vpb/latest_VPB.jpg", link: "https://www.hko.gov.hk/tc/wxinfo/ts/webcam/VPB_photo.htm" },
    { name: "環球貿易廣場 (望向東南面)", img: "https://www.hko.gov.hk/wxinfo/aws/hko_mica/ic1/latest_IC1.jpg", link: "https://www.hko.gov.hk/tc/wxinfo/ts/webcam/IC1_photo.htm" },
    { name: "環球貿易廣場 (西南面)", img: "https://www.hko.gov.hk/wxinfo/aws/hko_mica/ic2/latest_IC2.jpg", link: "https://www.hko.gov.hk/tc/wxinfo/ts/webcam/IC2_photo.htm" },
    { name: "清水灣 (向東)", img: "https://www.hko.gov.hk/wxinfo/aws/hko_mica/cwb/latest_CWB.jpg", link: "https://www.hko.gov.hk/tc/wxinfo/ts/webcam/CWB_photo.htm" },
    { name: "中環 (維多利亞港)", img: "https://www.hko.gov.hk/wxinfo/aws/hko_mica/cp1/latest_CP1.jpg", link: "https://www.hko.gov.hk/tc/wxinfo/ts/webcam/CP1_photo.htm" },
    { name: "流浮山 (望向西面)", img: "https://www.hko.gov.hk/wxinfo/aws/hko_mica/lfs/latest_LFS.jpg", link: "https://www.hko.gov.hk/tc/wxinfo/ts/webcam/LFS_photo.htm" },
    { name: "大帽山 (望向西南面)", img: "https://www.hko.gov.hk/wxinfo/aws/hko_mica/tm2/latest_TM2.jpg", link: "https://www.hko.gov.hk/tc/wxinfo/ts/webcam/TM2_photo.htm" },
    { name: "大帽山 (望向東北面)", img: "https://www.hko.gov.hk/wxinfo/aws/hko_mica/tm3/latest_TM3.jpg", link: "https://www.hko.gov.hk/tc/wxinfo/ts/webcam/TM3_photo.htm" },
    { name: "坪洲 (遠眺維多利亞港)", img: "https://www.hko.gov.hk/wxinfo/aws/hko_mica/pe2/latest_PE2.jpg", link: "https://www.hko.gov.hk/tc/wxinfo/ts/webcam/PE2_photo.htm" }
];

let currentPhotoIndex = 0;
function displayPhoto(i) {
    document.getElementById('photo-title').innerText = weatherPhotos[i].name;
    document.getElementById('photo-link').href = weatherPhotos[i].link;
    document.getElementById('hko-photo').src = `${weatherPhotos[i].img}?t=${Date.now()}`;
}
function nextPhoto() { currentPhotoIndex = (currentPhotoIndex + 1) % weatherPhotos.length; displayPhoto(currentPhotoIndex); }
function prevPhoto() { currentPhotoIndex = (currentPhotoIndex - 1 + weatherPhotos.length) % weatherPhotos.length; displayPhoto(currentPhotoIndex); }
function refreshCurrentPhoto() { displayPhoto(currentPhotoIndex); }
displayPhoto(0);

function updateTimestamp() {
    document.getElementById('update-time').innerText = `最後更新時間：${new Date().toLocaleString('zh-HK', { hour12: false }).replace(/\//g, '-')}`;
    updateAstronomicalData();
}

initAqiMap();
fetchNineDayForecast();
fetchTideData();
fetchRhrReadData();
loadLunarCalendarData();
fetchWeatherWarnings(); // 初始化載入天氣警告

setInterval(updateTimestamp, 1000);

const targetStations = [
    "香港天文台", 
    "九龍城", 
    "打鼓嶺", 
    "赤鱲角", 
    "赤柱", 
    "屯門", 
    "將軍澳", 
    "西貢"
];

let currentStationIndex = 0;
let rawTemperatureData = [];

function prevStation() {
    currentStationIndex = (currentStationIndex - 1 + targetStations.length) % targetStations.length;
    updateStationDisplay();
}

function nextStation() {
    currentStationIndex = (currentStationIndex + 1) % targetStations.length;
    updateStationDisplay();
}

function updateStationDisplay() {
    const currentStation = targetStations[currentStationIndex];
    document.getElementById('summary-station-name').innerText = currentStation;

    if (rawTemperatureData && rawTemperatureData.length > 0) {
        const found = rawTemperatureData.find(item => item.place.includes(currentStation));
        if (found) {
            document.getElementById('summary-current-temp').innerText = `${found.value}°C`;
        } else {
            document.getElementById('summary-current-temp').innerText = `--°C`;
        }
    }
}

async function fetchRhrReadData() {
    try {
        const res = await fetch('https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=tc');
        if (res.ok) {
            const data = await res.json();
            
            if (data.temperature && data.temperature.data) {
                rawTemperatureData = data.temperature.data;
                updateStationDisplay();
            }

            if (data.humidity && data.humidity.data && data.humidity.data.length > 0) {
                const hkoHumObj = data.humidity.data.find(h => h.place.includes('香港天文台'));
                if (hkoHumObj) {
                    document.getElementById('summary-current-hum').innerText = `${hkoHumObj.value}%`;
                }
            }

            let uvDisplay = "--";
            if (data.uvindex) {
                if (typeof data.uvindex === 'string') {
                    uvDisplay = data.uvindex;
                } else if (data.uvindex.data && data.uvindex.data.length > 0) {
                    const firstUv = data.uvindex.data[0];
                    uvDisplay = firstUv.value !== undefined ? firstUv.value : (firstUv.desc || "--");
                } else if (data.uvindex.val) {
                    uvDisplay = data.uvindex.val;
                }
            }
            document.getElementById('summary-uv-text').innerText = `紫外線指數: ${uvDisplay}`;

            let updateTime = data.updateTime ? data.updateTime.substring(11, 16) : "--:--";
            document.getElementById('summary-update-time').innerText = `${updateTime} 更新`;
        }
    } catch (err) {
        console.error("天氣報告載入失敗", err);
    }
}