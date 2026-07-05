import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify

# CRITICAL: This must be completely unindented against the left wall
app = Flask(__name__)

LAT = 46.6358
LON = 8.5980

import requests
from flask import Flask, jsonify

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
    # Switching to the dedicated official live summary page
    url = "https://live.andermatt-sedrun-disentis.ch/"
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
        # Split the text by lines to isolate data blocks
        lines = response.text.split('\n')
        
        for lift in target_lifts:
            status = "Closed"
            
            # Find the specific line that mentions our lift
            for line in lines:
                if lift.lower() in line.lower():
                    # Now we check for runtime status indicators *only* on this line
                    # In the off-season, it lists operating hours as "00:00" or notes it's closed
                    if "00:00" in line or "closed" in line.lower() or "nicht in betrieb" in line.lower():
                        status = "Closed"
                    elif "open" in line.lower() or "betrieb ab" in line.lower() or "in betrieb" in line.lower():
                        # Double-check it's not zeroed out operational hours
                        if "00:00" not in line:
                            status = "Open"
                            
            lifts_status.append({"name": lift, "status": status})
            
    except Exception:
        for lift in target_lifts:
            lifts_status.append({"name": lift, "status": "Offline"})
            
    return lifts_status

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
