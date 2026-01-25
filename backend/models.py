from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from database import Base


class ClothingItem(Base):
    __tablename__ = "clothing_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)  # e.g., "top", "bottom", "shoes", "outerwear", "accessory"
    subcategory = Column(String)  # e.g., "t-shirt", "jeans", "sneakers"
    color = Column(String)
    material = Column(String)
    pattern = Column(String)  # e.g., "solid", "striped", "floral"
    style = Column(String)  # e.g., "casual", "formal", "sporty", "bohemian"
    weather_suitability = Column(JSON)  # e.g., ["hot", "warm", "cool", "cold"]
    occasion_suitability = Column(JSON)  # e.g., ["casual", "work", "formal", "party", "workout"]
    description = Column(String)  # AI-generated description
    image_path = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "subcategory": self.subcategory,
            "color": self.color,
            "material": self.material,
            "pattern": self.pattern,
            "style": self.style,
            "weather_suitability": self.weather_suitability,
            "occasion_suitability": self.occasion_suitability,
            "description": self.description,
            "image_path": self.image_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
