import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify

# CRITICAL: This must be completely unindented against the left wall
app = Flask(__name__)

LAT = 46.6358
LON = 8.5980

def get_mountain_weather():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current=temperature_2m,weather_code,snow_depth&daily=snowfall_sum&timezone=Europe/Zurich"
    try:
        r = requests.get(url).json()
        current = r.get("current", {})
        daily = r.get("daily", {})
        
        code = current.get("weather_code", 0)
        condition = "Clear" if code == 0 else "Cloudy" if code in [1,2,3] else "Snowing" if code in [71,73,75,85,86] else "Mixed"
        
        return {
            "temp": round(current.get("temperature_2m", 0)),
            "condition": condition,
            "snow_depth_cm": round(current.get("snow_depth", 0) * 100),
            "new_snow_cm": round(daily.get("snowfall_sum", [0])[0])
        }
    except Exception:
        return {"temp": "--", "condition": "Unknown", "snow_depth_cm": "--", "new_snow_cm": "0"}

def get_gemsstock_lifts():
    url = "https://snow.myswitzerland.com/snow_reports/andermatt-oberalp-sedrun-111/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    target_lifts = [
        "Gemsstock-Bahn", 
        "Gurschen-Bahn", 
        "Gurschen-Flyer", 
        "Lutersee-Lift", 
        "Gletscherchele"
    ]
    
    lifts_status = []
    try:
        response = requests.get(url, headers=headers)
        page_text = response.text.lower()
        
        for lift in target_lifts:
            status = "Closed"
            if lift.lower() in page_text:
                # Basic scraper fallback mechanism
                if "open" in page_text or "in betrieb" in page_text:
                    status = "Open"
            lifts_status.append({"name": lift, "status": status})
            
    except Exception:
        for lift in target_lifts:
            lifts_status.append({"name": lift, "status": "Offline"})
            
    return lifts_status

# Changed to the root path '/' for simple Vercel mapping
@app.route("/")
def handle_endpoint():
    weather_data = get_mountain_weather()
    lifts_data = get_gemsstock_lifts()
    open_count = sum(1 for l in lifts_data if l["status"] == "Open")
    
    return jsonify({
        "weather": weather_data,
        "lifts": lifts_data,
        "summary": {
            "open": open_count,
            "total": len(lifts_data)
        }
    })

# We remove the traditional app.run() block because Vercel handles 
# execution via its own built-in serverless wrapper.
