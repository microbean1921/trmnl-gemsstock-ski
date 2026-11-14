import re
import requests
import datetime
from flask import Flask, jsonify, send_file

app = Flask(__name__)

LAT = 46.6358
LON = 8.5980

def get_mountain_weather():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}¤t=temperature_2m,weather_code&hourly=snow_depth&daily=snowfall_sum,weather_code,temperature_2m_max,temperature_2m_min&timezone=Europe/Zurich"
    
    try:
        r = requests.get(url, timeout=10).json()
        current = r.get("current", {})
        daily = r.get("daily", {})
        hourly = r.get("hourly", {})
        
        base_temp = round(current.get("temperature_2m", 0))
        peak_temp = base_temp - 10
        
        code = current.get("weather_code", 0)
        condition = "Clear" if code == 0 else "Cloudy" if code in [1,2,3] else "Snowing" if code in [71,73,75,85,86] else "Mixed"
        
        snow_depth_list = hourly.get("snow_depth", [0])
        snow_depth_cm = round(snow_depth_list[0] * 100) if snow_depth_list else 0
        new_snow_cm = round(daily.get("snowfall_sum", [0])[0])
        
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
    url = "https://live.andermatt-sedrun-disentis.ch/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    # Map dashboard display names to flexible regex patterns (handles hyphen/no-hyphen variants)
    target_lifts = [
        ("Gemsstock-Bahn", r"gemsstock[- ]?bahn"),
        ("Gurschen-Bahn", r"gurschen[- ]?bahn"),
        ("Gurschen-Flyer", r"gurschen[- ]?flyer"),
        ("Lutersee-Lift", r"lutersee([- ]?lift)?")
    ]
    
    open_indicators = [
        "in betrieb", "geöffnet", "offen", '"open"', "'open'",
        "status-open", "state-open", "is-open", "betrieb ab"
    ]
    closed_indicators = [
        "nicht in betrieb", "geschlossen", '"closed"', "'closed'",
        "status-closed", "state-closed", "00:00 - 00:00", "00:00-00:00"
    ]
    
    lifts_status = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        html = response.text
        
        for display_name, pattern in target_lifts:
            status = "Closed"
            for match in re.finditer(pattern, html, re.IGNORECASE):
                start = max(0, match.start() - 100)
                end = min(len(html), match.end() + 450)
                snippet = html[start:end].lower()
                
                is_closed = any(ind in snippet for ind in closed_indicators)
                has_hours = bool(re.search(r"\b0[789]:\d{2}\s*-\s*1[567]:\d{2}\b", snippet))
                is_open = any(ind in snippet for ind in open_indicators) or has_hours
                
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
    url = "https://live.andermatt-sedrun-disentis.ch/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    r = requests.get(url, headers=headers, timeout=10)
    idx = r.text.lower().find("gemsstock")
    sample = r.text[max(0, idx - 200):idx + 1200] if idx != -1 else r.text[:1500]
    return jsonify({
        "status_code": r.status_code,
        "found_gemsstock": idx != -1,
        "html_sample": sample
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
