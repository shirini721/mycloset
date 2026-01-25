import httpx
from typing import Optional
import os

# Using Open-Meteo API (free, no API key required)
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


async def get_coordinates(city: str) -> Optional[dict]:
    """Get latitude and longitude for a city name."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                GEOCODING_URL, params={"name": city, "count": 1, "format": "json"}
            )
            response.raise_for_status()
            data = response.json()

            if "results" in data and len(data["results"]) > 0:
                result = data["results"][0]
                return {
                    "latitude": result["latitude"],
                    "longitude": result["longitude"],
                    "name": result["name"],
                    "country": result.get("country", ""),
                }
            return None
        except Exception as e:
            print(f"Error fetching coordinates: {e}")
            return None


async def get_weather(location: str) -> Optional[dict]:
    """
    Get current weather for a location.
    Returns weather data including temperature, conditions, and clothing recommendations.
    """
    coords = await get_coordinates(location)
    if not coords:
        return None

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                WEATHER_URL,
                params={
                    "latitude": coords["latitude"],
                    "longitude": coords["longitude"],
                    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
                    "temperature_unit": "fahrenheit",
                    "wind_speed_unit": "mph",
                },
            )
            response.raise_for_status()
            data = response.json()

            current = data.get("current", {})
            temp = current.get("temperature_2m", 70)
            feels_like = current.get("apparent_temperature", temp)
            humidity = current.get("relative_humidity_2m", 50)
            precipitation = current.get("precipitation", 0)
            weather_code = current.get("weather_code", 0)
            wind_speed = current.get("wind_speed_10m", 0)

            # Map weather code to description
            weather_description = map_weather_code(weather_code)

            # Determine weather category for clothing
            weather_category = get_weather_category(temp, precipitation)

            # Check if it's rainy
            is_rainy = precipitation > 0 or weather_code in [
                51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99
            ]

            return {
                "location": f"{coords['name']}, {coords['country']}",
                "temperature": round(temp),
                "feels_like": round(feels_like),
                "humidity": humidity,
                "precipitation": precipitation,
                "wind_speed": round(wind_speed),
                "description": weather_description,
                "weather_category": weather_category,
                "is_rainy": is_rainy,
                "clothing_recommendation": get_clothing_recommendation(
                    temp, is_rainy, wind_speed
                ),
            }
        except Exception as e:
            print(f"Error fetching weather: {e}")
            return None


def map_weather_code(code: int) -> str:
    """Map WMO weather code to human-readable description."""
    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return weather_codes.get(code, "Unknown")


def get_weather_category(temp: float, precipitation: float) -> list[str]:
    """
    Map temperature to clothing-appropriate weather categories.
    Returns list of suitable weather tags.
    """
    categories = []

    if temp >= 85:
        categories.append("hot")
    elif temp >= 70:
        categories.append("warm")
    elif temp >= 55:
        categories.append("mild")
    elif temp >= 40:
        categories.append("cool")
    else:
        categories.append("cold")

    if precipitation > 0:
        categories.append("rainy")

    return categories


def get_clothing_recommendation(temp: float, is_rainy: bool, wind_speed: float) -> str:
    """Get a general clothing recommendation based on weather."""
    recommendations = []

    if temp >= 85:
        recommendations.append("Light, breathable clothing recommended")
    elif temp >= 70:
        recommendations.append("Light layers, short sleeves work well")
    elif temp >= 55:
        recommendations.append("Consider a light jacket or long sleeves")
    elif temp >= 40:
        recommendations.append("Warm layers recommended, consider a coat")
    else:
        recommendations.append("Heavy coat and warm layers essential")

    if is_rainy:
        recommendations.append("Don't forget an umbrella or rain jacket")

    if wind_speed > 20:
        recommendations.append("It's windy - a windbreaker might help")

    return ". ".join(recommendations)
