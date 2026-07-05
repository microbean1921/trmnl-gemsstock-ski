import requests
import datetime
from flask import Flask, jsonify, send_file

app = Flask(__name__)

LAT = 46.6358
LON = 8.5980

def get_mountain_weather():
    url_base = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&elevation=1444&current=temperature_2m,weather_code&timezone=Europe/Zurich"
    
    # Expanded to request future maximum/minimum daily temperatures and weather conditions
    url_peak = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&elevation=2961&current=temperature_2m,snow_depth&daily=snowfall_sum,weather_code,temperature_2m_max,temperature_2m_min&timezone=Europe/Zurich"
    
    try:
        r_base = requests.get(url_base).json()
        r_peak = requests.get(url_peak).json()
        
        c_base = r_base.get("current", {})
        c_peak = r_peak.get("current", {})
        daily = r_peak.get("daily", {})
        
        code = c_base.get("weather_code", 0)
        condition = "Clear" if code == 0 else "Cloudy" if code in [1,2,3] else "Snowing" if code in [71,73,75,85,86] else "Mixed"
        
        # Parse out the rolling 3-day future forecast (skipping index 0 which is today)
        forecast_list = []
        f_times = daily.get("time", [])
        f_codes = daily.get("weather_code", [])
        f_maxes = daily.get("temperature_2m_max", [])
        f_mins = daily.get("temperature_2m_min", [])
        
        for i in range(1, 4):
            if i < len(f_times):
                day_dt = datetime.datetime.strptime(f_times[i], "%Y-%m-%d")
                day_name = day_dt.strftime("%a") # Returns "Mon", "Tue", etc.
                
                f_code = f_codes[i] if i < len(f_codes) else 0
                f_cond = "Clear" if f_code == 0 else "Cloudy" if f_code in [1,2,3] else "Snow" if f_code in [71,73,75,85,86] else "Rain"
                
                forecast_list.append({
                    "day": day_name,
                    "max": round(f_maxes[i]) if i < len(f_maxes) else "--",
                    "min": round(f_mins[i]) if i < len(f_mins) else "--",
                    "condition": f_cond
                })
        
        return {
            "base_temp": round(c_base.get("temperature_2m", 0)),
            "peak_temp": round(c_peak.get("temperature_2m", 0)),
            "condition": condition,
            "snow_depth_cm": round(c_peak.get("snow_depth", 0) * 100),
            "new_snow_cm": round(daily.get("snowfall_sum", [0])[0]),
            "forecast": forecast_list
        }
    except Exception:
        return {"base_temp": "--", "peak_temp": "--", "condition": "Unknown", "snow_depth_cm": "--", "new_snow_cm": "0", "forecast": []}

def get_gemsstock_lifts():
    url = "https://live.andermatt-sedrun-disentis.ch/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    target_lifts = ["Gemsstock-Bahn", "Gurschen-Bahn", "Gurschen-Flyer", "Lutersee-Lift"]
    lifts_status = []
    try:
        response = requests.get(url, headers=headers)
        lines = response.text.split('\n')
        
        for lift in target_lifts:
            status = "Closed"
            for line in lines:
                if lift.lower() in line.lower():
                    if "00:00" in line or "closed" in line.lower() or "nicht in betrieb" in line.lower():
                        status = "Closed"
                    elif "open" in line.lower() or "betrieb ab" in line.lower() or "in betrieb" in line.lower():
                        if "00:00" not in line:
                            status = "Open"
            lifts_status.append({"name": lift, "status": status})
    except Exception:
        for lift in target_lifts:
            lifts_status.append({"name": lift, "status": "Offline"})
    return lifts_status

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
