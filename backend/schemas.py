from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ClothingItemBase(BaseModel):
    name: str
    category: str
    subcategory: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    pattern: Optional[str] = None
    style: Optional[str] = None
    weather_suitability: Optional[list[str]] = None
    occasion_suitability: Optional[list[str]] = None
    description: Optional[str] = None


class ClothingItemCreate(ClothingItemBase):
    pass


class ClothingItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    pattern: Optional[str] = None
    style: Optional[str] = None
    weather_suitability: Optional[list[str]] = None
    occasion_suitability: Optional[list[str]] = None
    description: Optional[str] = None


class ClothingItemResponse(ClothingItemBase):
    id: int
    image_path: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RecommendationRequest(BaseModel):
    event_type: str  # e.g., "work", "date", "casual", "party", "workout", "wedding"
    weather: Optional[str] = None  # If not provided, will fetch current weather
    location: Optional[str] = None  # City name for weather lookup
    additional_preferences: Optional[str] = None  # Any extra user input


class OutfitRecommendation(BaseModel):
    outfit_name: str
    items: list[ClothingItemResponse]
    reasoning: str
    style_notes: Optional[str] = None


class RecommendationResponse(BaseModel):
    weather_info: dict
    event_type: str
    recommendations: list[OutfitRecommendation]


class ImageAnalysisResult(BaseModel):
    name: str
    category: str
    subcategory: str
    color: str
    material: str
    pattern: str
    style: str
    weather_suitability: list[str]
    occasion_suitability: list[str]
    description: str
