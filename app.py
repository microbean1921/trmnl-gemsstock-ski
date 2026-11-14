import re
import requests
import datetime
from flask import Flask, jsonify, send_file

app = Flask(__name__)

LAT = 46.6358
LON = 8.5980
SIS_FEED_URL = "https://export.siscontrol.ch/sismedia/json/8927FB40-50DA-4BAF-B085-EDCFE671BCFA"

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

def _collect_items(node, found):
    if isinstance(node, dict):
        node_id = node.get("id")
        if node_id in [261, 262, 263, 264]:
            found[node_id] = node
        for v in node.values():
            _collect_items(v, found)
    elif isinstance(node, list):
        for item in node:
            _collect_items(item, found)

def _parse_status(item):
    if not item:
        return "Closed"
    raw = None
    for key in ["status", "state", "statusId", "stateId", "operationStatus", "isOpen", "open"]:
        if key in item and item[key] is not None:
            raw = item[key]
            break
    if isinstance(raw, dict):
        raw = raw.get("id") or raw.get("code") or raw.get("status") or raw.get("name")
    if isinstance(raw, str):
        raw_clean = raw.strip().lower()
        return "Open" if raw_clean in ["1", "open", "opened", "true", "geöffnet", "in betrieb"] else "Closed"
    return "Open" if raw in [1, True] else "Closed"

def get_gemsstock_lifts():
    id_map = [
        (262, "Gemsstock-Bahn"),
        (261, "Gurschen-Bahn"),
        (263, "Gurschen-Flyer"),
        (264, "Lutersee-Lift")
    ]
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        data = requests.get(SIS_FEED_URL, headers=headers, timeout=10).json()
        found = {}
        _collect_items(data, found)

        # Match by lift name if IDs are ordered differently in SIS Control
        name_to_status = {}
        for item in found.values():
            label = str(item.get("name") or item.get("title") or item.get("label") or "").lower()
            st = _parse_status(item)
            if "gemsstock" in label:
                name_to_status["Gemsstock-Bahn"] = st
            elif "flyer" in label:
                name_to_status["Gurschen-Flyer"] = st
            elif "gurschen" in label:
                name_to_status["Gurschen-Bahn"] = st
            elif "lutersee" in label:
                name_to_status["Lutersee-Lift"] = st

        result = []
        for lift_id, display_name in id_map:
            if display_name in name_to_status:
                status = name_to_status[display_name]
            else:
                status = _parse_status(found.get(lift_id))
            result.append({"name": display_name, "status": status})
        return result
    except Exception:
        return [{"name": name, "status": "Offline"} for _, name in id_map]

@app.route("/debug")
def debug_scrape():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    r = requests.get(SIS_FEED_URL, headers=headers, timeout=10)
    data = r.json()
    found = {}
    _collect_items(data, found)
    return jsonify({
        "status_code": r.status_code,
        "top_level_keys": list(data.keys()) if isinstance(data, dict) else type(data).__name__,
        "gemsstock_lift_objects": found
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
