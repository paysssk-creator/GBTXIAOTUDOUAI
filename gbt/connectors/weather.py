"""weather.py — Weather connector (Open-Meteo free API)"""
import urllib.request, json

def current_weather(city="Beijing", lat=None, lon=None):
    COORDS = {"Beijing": (39.9, 116.4), "Shanghai": (31.2, 121.5), "Shenzhen": (22.5, 114.1),
              "Guangzhou": (23.1, 113.3), "Chengdu": (30.6, 104.1), "Hangzhou": (30.3, 120.2)}
    if not lat: lat, lon = COORDS.get(city, (39.9, 116.4))
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code&timezone=auto"
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        c = data.get("current", {})
        return {"ok": True, "city": city, "temperature": c.get("temperature_2m"), "humidity": c.get("relative_humidity_2m"), "wind_speed": c.get("wind_speed_10m")}
    except Exception as e: return {"ok": False, "error": str(e)}

def forecast(city="Beijing", days=3, lat=None, lon=None):
    COORDS = {"Beijing": (39.9, 116.4), "Shanghai": (31.2, 121.5), "Shenzhen": (22.5, 114.1)}
    if not lat: lat, lon = COORDS.get(city, (39.9, 116.4))
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,weather_code&forecast_days={days}&timezone=auto"
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        daily = data.get("daily", {})
        days_data = [{"date": daily["time"][i], "max": daily["temperature_2m_max"][i], "min": daily["temperature_2m_min"][i]} for i in range(min(days, len(daily.get("time",[]))))]
        return {"ok": True, "city": city, "forecast": days_data}
    except Exception as e: return {"ok": False, "error": str(e)}

def weather_handle(action, **params):
    h = {"current": lambda: current_weather(params.get("city","Beijing"), params.get("lat"), params.get("lon")),
         "forecast": lambda: forecast(params.get("city","Beijing"), params.get("days",3))}.get(action)
    return h() if h else {"ok": False, "error": f"Unknown: {action}"}
