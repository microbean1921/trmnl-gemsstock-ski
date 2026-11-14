import requests
import datetime
from flask import Flask, jsonify, send_file

app = Flask(__name__)

SIS_FEED_URL = "https://export.siscontrol.ch/sismedia/json/8927FB40-50DA-4BAF-B085-EDCFE671BCFA"

GEMSSTOCK_IDS = [261, 262, 263, 264]
SEDRUN_IDS = [265, 266, 267, 268, 269, 270, 429, 271, 272, 273, 274, 275, 276]


def get_mountain_weather(lat, lon, lapse_rate_c):
    params = {
        "latitude": lat,
        "longitude": lon,
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
        peak_temp = base_temp - lapse_rate_c

        code = current.get("weather_code", 0)
        condition = (
            "Clear" if code == 0
            else "Cloudy" if code in [1, 2, 3]
            else "Snowing" if code in [71, 73, 75, 85, 86]
            else "Mixed"
        )

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
                f_cond = (
                    "Clear" if f_code == 0
                    else "Cloudy" if f_code in [1, 2, 3]
                    else "Snow" if f_code in [71, 73, 75, 85, 86]
                    else "Rain"
                )

                day_max = round(f_maxes[i]) - lapse_rate_c if i < len(f_maxes) else 0
                day_min = round(f_mins[i]) - lapse_rate_c if i < len(f_mins) else 0

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
        return {
            "base_temp": "--",
            "peak_temp": "--",
            "condition": "Unknown",
            "snow_depth_cm": "--",
            "new_snow_cm": "0",
            "forecast": []
        }


def _collect_items(node, target_ids, found):
    if isinstance(node, dict):
        node_id = node.get("id")
        if node_id in target_ids and "status" in node:
            found[node_id] = node
        for v in node.values():
            _collect_items(v, target_ids, found)
    elif isinstance(node, list):
        for item in node:
            _collect_items(item, target_ids, found)


def _is_status_open(status_code, status_types):
    if isinstance(status_types, list):
        for st in status_types:
            if isinstance(st, dict) and st.get("id") == status_code:
                name_obj = st.get("name", {})
                label = (
                    " ".join(str(v) for v in name_obj.values()).lower()
                    if isinstance(name_obj, dict)
                    else str(name_obj).lower()
                )
                if any(w in label for w in ["open", "geöffnet", "offen", "betrieb"]):
                    return True
                if any(w in label for w in ["closed", "geschlossen", "vorbereitung"]):
                    return False
    return status_code == 2


def fetch_sis_lifts(target_ids, ordered_pairs=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    data = requests.get(SIS_FEED_URL, headers=headers, timeout=10).json()
    status_types = data.get("statusTypes", []) if isinstance(data, dict) else []

    found = {}
    _collect_items(data, target_ids, found)

    result = []
    if ordered_pairs:
        for lift_id, display_name in ordered_pairs:
            item = found.get(lift_id, {})
            is_open = _is_status_open(item.get("status"), status_types)
            result.append({
                "id": lift_id,
                "name": display_name,
                "status": "Open" if is_open else "Closed"
            })
    else:
        for lift_id in target_ids:
            item = found.get(lift_id)
            if not item:
                continue
            name_obj = item.get("name", {})
            display_name = (
                name_obj.get("de") or name_obj.get("en") or f"Lift {lift_id}"
                if isinstance(name_obj, dict)
                else str(name_obj)
            )
            is_open = _is_status_open(item.get("status"), status_types)
            result.append({
                "id": lift_id,
                "name": display_name,
                "status": "Open" if is_open else "Closed"
            })
    return result


@app.route("/logo.svg")
def serve_logo():
    return send_file("image_454c6a.svg", mimetype="image/svg+xml")


@app.route("/")
def handle_gemsstock():
    weather_data = get_mountain_weather(lat=46.6358, lon=8.5980, lapse_rate_c=10)
    gemsstock_order = [
        (262, "Gemsstock-Bahn"),
        (261, "Gurschen-Bahn"),
        (263, "Gurschen-Flyer"),
        (264, "Lutersee-Lift")
    ]
    try:
        lifts_data = fetch_sis_lifts(GEMSSTOCK_IDS, ordered_pairs=gemsstock_order)
    except Exception:
        lifts_data = [{"name": name, "status": "Offline"} for _, name in gemsstock_order]

    return jsonify({
        "weather": weather_data,
        "lifts": lifts_data,
        "summary": {
            "open": sum(1 for l in lifts_data if l["status"] == "Open"),
            "total": len(lifts_data)
        }
    })


@app.route("/sedrun")
def handle_sedrun():
    # Centered on Guetsch / Oberalppass / Cuolm Val ridge (2600m Schneehuenerstock peak)
    weather_data = get_mountain_weather(lat=46.6589, lon=8.6714, lapse_rate_c=8)
    try:
        lifts_data = fetch_sis_lifts(SEDRUN_IDS)
    except Exception:
        lifts_data = [{"name": "Feed Offline", "status": "Offline"}]

    return jsonify({
        "weather": weather_data,
        "lifts": lifts_data,
        "summary": {
            "open": sum(1 for l in lifts_data if l["status"] == "Open"),
            "total": len(lifts_data)
        }
    })


@app.route("/discover")
def discover_sedrun_lifts():
    lifts_data = fetch_sis_lifts(SEDRUN_IDS)
    return jsonify({
        "count": len(lifts_data),
        "lifts": lifts_data
    })
