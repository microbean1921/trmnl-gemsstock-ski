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
    url = "https://www.andermatt-sedrun-disentis.ch/de/stories/betriebszeiten"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    target_lifts = [
        ("Gemsstock-Bahn", r"gemsstock[- ]?bahn"),
        ("Gurschen-Bahn", r"gurschen[- ]?bahn"),
        ("Gurschen-Flyer", r"gurschen[- ]?flyer"),
        ("Lutersee-Lift", r"lutersee([- ]?lift)?")
    ]
    
    open_tokens = [
        "geöffnet", "in betrieb", "offen", '"open"', "'open'",
        '"isopen":true', '"status":"open"', '"state":1', '"status":1', "status-open"
    ]
    closed_tokens = [
        "geschlossen", "nicht in betrieb", '"closed"', "'closed'",
        '"isopen":false', '"status":"closed"', '"state":0', '"status":0', "status-closed"
    ]
    
    lifts_status = []
    try:
        r = requests.get(url, headers=headers, timeout=10)
        html = r.text
        
        for display_name, pattern in target_lifts:
            status = "Closed"
            for match in re.finditer(pattern, html, re.IGNORECASE):
                snippet = html[max(0, match.start() - 150):min(len(html), match.end() + 400)].lower()
                is_closed = any(tok in snippet for tok in closed_tokens)
                is_open = any(tok in snippet for tok in open_tokens)
                if is_open and not is_closed:
                    status = "Open"
                    break
            lifts_status.append({"name": display_name, "status": status})
    except Exception:
        for display_name, _ in target_lifts:
            lifts_status.append({"name": display_name, "status": "Offline"})
            
    return lifts_status

@app.route("/debug")
def debug_scrape():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    out = {}

    try:
        r1 = requests.get("https://www.andermatt-sedrun-disentis.ch/de/stories/betriebszeiten", headers=headers, timeout=10)
        html_lower = r1.text.lower()
        samples = {}
        for term in ["gurschen", "gemsstock-bahn", "gemsstockbahn", "lutersee", "siscontrol"]:
            idx = html_lower.find(term)
            if idx != -1:
                samples[term] = r1.text[max(0, idx - 200):idx + 500]
        out["betriebszeiten_status"] = r1.status_code
        out["betriebszeiten_found"] = list(samples.keys())
        out["betriebszeiten_samples"] = samples
    except Exception as e:
        out["betriebszeiten_error"] = str(e)

    try:
        r2 = requests.get("https://prodmediacenter.blob.core.windows.net/a005/ledwall/areaview.html", headers=headers, timeout=10)
        src_urls = re.findall(r'src=["\']([^"\']+)["\']', r2.text, re.IGNORECASE)
        out["areaview_raw_html"] = r2.text[:1500]
        out["areaview_src_urls"] = src_urls
    except Exception as e:
        out["areaview_error"] = str(e)

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
