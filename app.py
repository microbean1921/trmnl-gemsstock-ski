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
    r = requests.get(base + "areaview.html", headers=headers, timeout=10)
    js_files = sorted(list(set(re.findall(r'src=["\']([^"\']+\.js)["\']', r.text, re.IGNORECASE))))

    found_urls = []
    json_refs = []
    for js in js_files:
        try:
            jr = requests.get(base + js, headers=headers, timeout=10)
            for m in re.findall(r'https?://[^"\'\s\)\]]+', jr.text):
                if not any(skip in m for skip in ["w3.org", "reactjs.org", "fb.me", "github.com", "mozilla.org"]):
                    found_urls.append(m)
            for m in re.findall(r'["\']([^"\'\s]+\.json[^"\'\s]*)["\']', jr.text):
                json_refs.append(m)
        except Exception as e:
            found_urls.append(f"ERROR {js}: {e}")

    return jsonify({
        "js_files": js_files,
        "found_urls": sorted(list(set(found_urls))),
        "json_refs": sorted(list(set(json_refs)))
    })

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
