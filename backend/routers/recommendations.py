from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from schemas import RecommendationRequest, RecommendationResponse
from services.weather import get_weather
from services.recommender import get_outfit_recommendations, rebuild_vector_store

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.post("", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest, db: Session = Depends(get_db)):
    """
    Get outfit recommendations based on weather and event type.

    - If location is provided, fetches current weather automatically
    - If weather is provided directly, uses that instead
    - Event types: work, casual, date, party, workout, formal, wedding, outdoor, beach
    """
    weather_info = None

    # Get weather info
    if request.location:
        weather_info = await get_weather(request.location)
        if not weather_info:
            raise HTTPException(
                status_code=400,
                detail=f"Could not fetch weather for location: {request.location}"
            )
    elif request.weather:
        # User provided weather description - parse it into a basic weather dict
        weather_info = parse_weather_description(request.weather)
    else:
        # Default to mild weather
        weather_info = {
            "location": "Unknown",
            "temperature": 70,
            "feels_like": 70,
            "humidity": 50,
            "precipitation": 0,
            "wind_speed": 5,
            "description": "Mild",
            "weather_category": ["mild"],
            "is_rainy": False,
            "clothing_recommendation": "Light layers work well"
        }

    # Get outfit recommendations
    recommendations = await get_outfit_recommendations(
        db=db,
        weather_info=weather_info,
        event_type=request.event_type,
        additional_preferences=request.additional_preferences
    )

    return RecommendationResponse(
        weather_info=weather_info,
        event_type=request.event_type,
        recommendations=[
            {
                "outfit_name": rec["outfit_name"],
                "items": rec["items"],
                "reasoning": rec["reasoning"],
                "style_notes": rec.get("style_notes")
            }
            for rec in recommendations
        ]
    )


@router.get("/weather/{location}")
async def get_weather_info(location: str):
    """Get current weather for a location."""
    weather_info = await get_weather(location)
    if not weather_info:
        raise HTTPException(
            status_code=400,
            detail=f"Could not fetch weather for location: {location}"
        )
    return weather_info


@router.post("/rebuild-index")
async def rebuild_search_index(db: Session = Depends(get_db)):
    """Rebuild the vector search index from all clothing items."""
    count = rebuild_vector_store(db)
    return {"message": f"Successfully rebuilt index with {count} items"}


def parse_weather_description(description: str) -> dict:
    """Parse a user-provided weather description into a weather dict."""
    description_lower = description.lower()

    # Determine temperature category
    if any(word in description_lower for word in ["hot", "scorching", "heat"]):
        temp = 90
        category = ["hot"]
    elif any(word in description_lower for word in ["warm", "sunny", "nice"]):
        temp = 75
        category = ["warm"]
    elif any(word in description_lower for word in ["cool", "crisp", "chilly"]):
        temp = 55
        category = ["cool"]
    elif any(word in description_lower for word in ["cold", "freezing", "frigid", "snow"]):
        temp = 35
        category = ["cold"]
    else:
        temp = 68
        category = ["mild"]

    # Check for rain
    is_rainy = any(word in description_lower for word in ["rain", "rainy", "wet", "storm", "drizzle"])
    if is_rainy:
        category.append("rainy")

    return {
        "location": "User specified",
        "temperature": temp,
        "feels_like": temp,
        "humidity": 50,
        "precipitation": 1 if is_rainy else 0,
        "wind_speed": 10,
        "description": description,
        "weather_category": category,
        "is_rainy": is_rainy,
        "clothing_recommendation": f"Based on your description: {description}"
    }
