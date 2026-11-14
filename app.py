import re
import requests
import datetime
from flask import Flask, jsonify, send_file

app = Flask(__name__)

LAT = 46.6358
LON = 8.5980

def get_mountain_weather():
    params = {
        "latitude": LAT,
        "longitude": LON,
        "current": "temperature_2m,weather_code",
        "hourly": "snow_depth",
        "daily": "snowfall_sum,weather_code,temperature_2m_max,temperature_2m_min",
        "timezone": "Europe/Zurich"
    }
    
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10).json()
        if r.get("error"):
            raise ValueError(r.get("reason", "Open-Meteo API error"))

        current = r.get("current", {})
        daily = r.get("daily", {})
        hourly = r.get("hourly", {})
        
        base_temp = round(current.get("temperature_2m", 0))
        peak_temp = base_temp - 10
        
        code = current.get("weather_code", 0)
        condition = "Clear" if code == 0 else "Cloudy" if code in [1,2,3] else "Snowing" if code in [71,73,75,85,86] else "Mixed"
        
        snow_depth_list = hourly.get("snow_depth", [])
        hourly_times = hourly.get("time", [])
        current_hour_prefix = current.get("time", "")[:13]
        depth_m = 0
        for idx, t in enumerate(hourly_times):
            if t.startswith(current_hour_prefix) and idx < len(snow_depth_list):
                depth_m = snow_depth_list[idx] or 0
                break
        if not depth_m and snow_depth_list:
            depth_m = snow_depth_list[0] or 0

        snow_depth_cm = round(depth_m * 100)
        new_snow_cm = round(daily.get("snowfall_sum", [0])[0] or 0)
        
        forecast_list = []
        f_times = daily.get("time", [])
        f_codes = daily.get("weather_code", [])
        f_maxes = daily.get("temperature_2m_max", [])
        f_mins = daily.get("temperature_2m_min", [])
        
        for i in range(1, 4):
            if i < len(f_times):
                day_dt = datetime.datetime.strptime(f_times[i], "%Y-%m-%d")
                day_name = day_dt.strftime("%a")
                
                f_code = f_codes[i] if i < len(f_codes) else 0
                f_cond = "Clear" if f_code == 0 else "Cloudy" if f_code in [1,2,3] else "Snow" if f_code in [71,73,75,85,86] else "Rain"
                
                day_max = round(f_maxes[i]) - 10 if i < len(f_maxes) else 0
                day_min = round(f_mins[i]) - 10 if i < len(f_mins) else 0
                
                forecast_list.append({
                    "day": day_name,
                    "max": day_max,
                    "min": day_min,
                    "condition": f_cond
                })
        
        return {
            "base_temp": base_temp,
            "peak_temp": peak_temp,
            "condition": condition,
            "snow_depth_cm": snow_depth_cm,
            "new_snow_cm": new_snow_cm,
            "forecast": forecast_list
        }
    except Exception:
        return {"base_temp": "--", "peak_temp": "--", "condition": "Unknown", "snow_depth_cm": "--", "new_snow_cm": "0", "forecast": []}

def get_gemsstock_lifts():
    target_lifts = ["Gemsstock-Bahn", "Gurschen-Bahn", "Gurschen-Flyer", "Lutersee-Lift"]
    return [{"name": lift, "status": "Closed"} for lift in target_lifts]

@app.route("/debug")
def debug_scrape():
    base = "https://prodmediacenter.blob.core.windows.net/a005/ledwall/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    out = {}

    for fname in ["areas.json", "locations.json"]:
        try:
            res = requests.get(base + fname, headers=headers, timeout=10)
            out[fname] = res.json() if res.status_code == 200 else res.status_code
        except Exception as e:
            out[fname] = str(e)

    js_snippets = []
    for js in ["areaview.f62060a4.js", "areaview.fafa871a.js", "MediaCenterAndermatt.2638f920.js", "MediaCenterAndermatt.977eadd3.js"]:
        try:
            text = requests.get(base + js, headers=headers, timeout=10).text
            for kw in ["api.siscontrol.ch", "export.siscontrol.ch", "areas.json", "locations.json"]:
                for m in re.finditer(re.escape(kw), text):
                    snippet = text[max(0, m.start() - 150):min(len(text), m.end() + 350)]
                    js_snippets.append({"file": js, "keyword": kw, "code": snippet})
        except Exception as e:
            js_snippets.append({"file": js, "error": str(e)})

    out["js_snippets"] = js_snippets
    return jsonify(out)

@app.route("/logo.svg")
def serve_logo():
    return send_file("image_454c6a.svg", mimetype="image/svg+xml")

@app.route("/")
def handle_endpoint():
    weather_data = get_mountain_weather()
    lifts_data = get_gemsstock_lifts()
    return jsonify({
        "weather": weather_data,
        "lifts": lifts_data,
        "summary": {"open": sum(1 for l in lifts_data if l["status"] == "Open"), "total": len(lifts_data)}
    })
