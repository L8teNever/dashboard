import requests
import logging

logger = logging.getLogger(__name__)

# Weather code descriptions in German
WEATHER_CODES = {
    0: "Klarer Himmel ☀️",
    1: "Überwiegend klar 🌤️",
    2: "Teilweise bewölkt ⛅",
    3: "Bedeckt ☁️",
    45: "Nebel 🌫️",
    48: "Raufrostnebel 🌫️",
    51: "Leichter Sprühregen 🌧️",
    53: "Mäßiger Sprühregen 🌧️",
    55: "Dichter Sprühregen 🌧️",
    61: "Leichter Regen 🌧️",
    63: "Mäßiger Regen 🌧️",
    65: "Starker Regen 🌧️",
    71: "Leichter Schneefall ❄️",
    73: "Mäßiger Schneefall ❄️",
    75: "Starker Schneefall ❄️",
    80: "Leichte Regenschauer 🌦️",
    81: "Mäßige Regenschauer 🌦️",
    82: "Heftige Regenschauer 🌧️",
    95: "Gewitter 🌩️",
    96: "Gewitter mit leichtem Hagel ⛈️",
    99: "Gewitter mit starkem Hagel ⛈️"
}

class WeatherService:
    def __init__(self, lat=52.52, lon=13.41, city_name="Berlin"):
        self.lat = lat
        self.lon = lon
        self.city_name = city_name

    def get_weather(self):
        """
        Fetch weather from Open-Meteo (Free public weather API, no API key required).
        Fallbacks to realistic mock data if offline.
        """
        url = f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lon}&current_weather=true&hourly=temperature_2m,precipitation_probability,weathercode&timezone=auto"
        try:
            res = requests.get(url, timeout=4)
            if res.status_code == 200:
                data = res.json()
                current = data.get("current_weather", {})
                hourly_data = data.get("hourly", {})
                
                temp = round(current.get("temperature", 21))
                wcode = current.get("weathercode", 2)
                wind = round(current.get("windspeed", 12))
                condition = WEATHER_CODES.get(wcode, "Bewölkt")
                
                times = hourly_data.get("time", [])
                temps = hourly_data.get("temperature_2m", [])
                rains = hourly_data.get("precipitation_probability", [])
                
                parsed_hourly = []
                for i in range(min(12, len(times))):
                    time_str = times[i].split("T")[-1][:5] if "T" in times[i] else f"{i:02d}:00"
                    t_val = round(temps[i]) if i < len(temps) else temp
                    r_val = round(rains[i]) if i < len(rains) else 10
                    
                    parsed_hourly.append({
                        "key": i + 1,
                        "time": time_str,
                        "temp": f"{t_val}°",
                        "rain": f"{r_val}%",
                        "highlight": r_val >= 40
                    })
                
                rain_prob = parsed_hourly[0]["rain"] if parsed_hourly else "15%"
                
                return {
                    "city": self.city_name,
                    "tempLabel": f"{temp}°",
                    "condition": condition,
                    "windLabel": f"{wind} km/h Wind",
                    "rainLabel": f"{rain_prob} Regen",
                    "hourly": parsed_hourly
                }
        except Exception as e:
            logger.warning(f"Live Weather API fetch failed, returning fallback mock weather: {e}")

        # Fallback Weather Data
        return {
            "city": self.city_name,
            "tempLabel": "22°",
            "condition": "Teilweise bewölkt ⛅",
            "windLabel": "14 km/h Wind",
            "rainLabel": "20% Regen",
            "hourly": [
                { "key": 1, "time": "08:00", "temp": "19°", "rain": "10%", "highlight": False },
                { "key": 2, "time": "11:00", "temp": "21°", "rain": "15%", "highlight": False },
                { "key": 3, "time": "14:00", "temp": "23°", "rain": "25%", "highlight": False },
                { "key": 4, "time": "16:00", "temp": "22°", "rain": "60%", "highlight": True },
                { "key": 5, "time": "18:00", "temp": "20°", "rain": "45%", "highlight": True },
                { "key": 6, "time": "20:00", "temp": "18°", "rain": "20%", "highlight": False }
            ]
        }

weather_service = WeatherService()
