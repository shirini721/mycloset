from sqlalchemy.orm import Session
from models import ClothingItem
from schemas import ClothingItemCreate, ClothingItemUpdate
from typing import Optional
import os


def get_all_clothes(db: Session, category: Optional[str] = None) -> list[ClothingItem]:
    """Get all clothing items, optionally filtered by category."""
    query = db.query(ClothingItem)
    if category:
        query = query.filter(ClothingItem.category == category)
    return query.order_by(ClothingItem.created_at.desc()).all()


def get_clothing_item(db: Session, item_id: int) -> Optional[ClothingItem]:
    """Get a single clothing item by ID."""
    return db.query(ClothingItem).filter(ClothingItem.id == item_id).first()


def create_clothing_item(
    db: Session, item_data: dict, image_path: Optional[str] = None
) -> ClothingItem:
    """Create a new clothing item."""
    db_item = ClothingItem(
        name=item_data.get("name"),
        category=item_data.get("category"),
        subcategory=item_data.get("subcategory"),
        color=item_data.get("color"),
        material=item_data.get("material"),
        pattern=item_data.get("pattern"),
        style=item_data.get("style"),
        weather_suitability=item_data.get("weather_suitability"),
        occasion_suitability=item_data.get("occasion_suitability"),
        description=item_data.get("description"),
        image_path=image_path,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_clothing_item(
    db: Session, item_id: int, update_data: ClothingItemUpdate
) -> Optional[ClothingItem]:
    """Update an existing clothing item."""
    db_item = get_clothing_item(db, item_id)
    if not db_item:
        return None

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_item, key, value)

    db.commit()
    db.refresh(db_item)
    return db_item


def delete_clothing_item(db: Session, item_id: int) -> bool:
    """Delete a clothing item."""
    db_item = get_clothing_item(db, item_id)
    if not db_item:
        return False

    # Delete the associated image file if it exists
    if db_item.image_path and os.path.exists(db_item.image_path):
        try:
            os.remove(db_item.image_path)
        except OSError:
            pass

    db.delete(db_item)
    db.commit()
    return True


def search_clothes(
    db: Session,
    weather: Optional[list[str]] = None,
    occasion: Optional[list[str]] = None,
    category: Optional[str] = None,
    style: Optional[str] = None,
) -> list[ClothingItem]:
    """
    Search clothing items by various criteria.
    This is used for initial filtering before RAG-based recommendation.
    """
    query = db.query(ClothingItem)

    if category:
        query = query.filter(ClothingItem.category == category)

    if style:
        query = query.filter(ClothingItem.style == style)

    items = query.all()

    # Filter by weather and occasion in Python (since we're using JSON fields)
    if weather:
        items = [
            item
            for item in items
            if item.weather_suitability
            and any(w in item.weather_suitability for w in weather)
        ]

    if occasion:
        items = [
            item
            for item in items
            if item.occasion_suitability
            and any(o in item.occasion_suitability for o in occasion)
        ]

    return items
