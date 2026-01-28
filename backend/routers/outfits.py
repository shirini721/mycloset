from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import SavedOutfit, ClothingItem
from schemas import (
    SavedOutfitCreate,
    SavedOutfitUpdate,
    SavedOutfitResponse,
    SavedOutfitListResponse,
    ClothingItemResponse,
)

router = APIRouter(prefix="/api/outfits", tags=["outfits"])


@router.get("/", response_model=List[SavedOutfitListResponse])
async def list_outfits(db: Session = Depends(get_db)):
    """List all saved outfits with preview info."""
    outfits = db.query(SavedOutfit).order_by(SavedOutfit.created_at.desc()).all()

    result = []
    for outfit in outfits:
        # Get preview images (first 4 items)
        preview_images = []
        if outfit.item_ids:
            items = db.query(ClothingItem).filter(
                ClothingItem.id.in_(outfit.item_ids[:4])
            ).all()
            preview_images = [item.image_path for item in items if item.image_path]

        result.append(SavedOutfitListResponse(
            id=outfit.id,
            name=outfit.name,
            description=outfit.description,
            item_count=len(outfit.item_ids) if outfit.item_ids else 0,
            preview_images=preview_images,
            created_at=outfit.created_at,
        ))

    return result


@router.post("/", response_model=SavedOutfitResponse)
async def create_outfit(outfit: SavedOutfitCreate, db: Session = Depends(get_db)):
    """Create a new saved outfit."""
    # Validate that all item IDs exist
    existing_items = db.query(ClothingItem).filter(
        ClothingItem.id.in_(outfit.item_ids)
    ).all()
    existing_ids = {item.id for item in existing_items}

    invalid_ids = set(outfit.item_ids) - existing_ids
    if invalid_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid clothing item IDs: {list(invalid_ids)}"
        )

    db_outfit = SavedOutfit(
        name=outfit.name,
        description=outfit.description,
        item_ids=outfit.item_ids,
    )
    db.add(db_outfit)
    db.commit()
    db.refresh(db_outfit)

    # Return with full item details
    items = [ClothingItemResponse.model_validate(item) for item in existing_items]

    return SavedOutfitResponse(
        id=db_outfit.id,
        name=db_outfit.name,
        description=db_outfit.description,
        item_ids=db_outfit.item_ids,
        items=items,
        created_at=db_outfit.created_at,
        updated_at=db_outfit.updated_at,
    )


@router.get("/{outfit_id}", response_model=SavedOutfitResponse)
async def get_outfit(outfit_id: int, db: Session = Depends(get_db)):
    """Get a saved outfit by ID with full item details."""
    outfit = db.query(SavedOutfit).filter(SavedOutfit.id == outfit_id).first()
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")

    # Get full item details
    items = []
    if outfit.item_ids:
        db_items = db.query(ClothingItem).filter(
            ClothingItem.id.in_(outfit.item_ids)
        ).all()
        items = [ClothingItemResponse.model_validate(item) for item in db_items]

    return SavedOutfitResponse(
        id=outfit.id,
        name=outfit.name,
        description=outfit.description,
        item_ids=outfit.item_ids,
        items=items,
        created_at=outfit.created_at,
        updated_at=outfit.updated_at,
    )


@router.put("/{outfit_id}", response_model=SavedOutfitResponse)
async def update_outfit(
    outfit_id: int,
    outfit_update: SavedOutfitUpdate,
    db: Session = Depends(get_db)
):
    """Update a saved outfit."""
    outfit = db.query(SavedOutfit).filter(SavedOutfit.id == outfit_id).first()
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")

    # Update fields if provided
    if outfit_update.name is not None:
        outfit.name = outfit_update.name
    if outfit_update.description is not None:
        outfit.description = outfit_update.description
    if outfit_update.item_ids is not None:
        # Validate new item IDs
        existing_items = db.query(ClothingItem).filter(
            ClothingItem.id.in_(outfit_update.item_ids)
        ).all()
        existing_ids = {item.id for item in existing_items}

        invalid_ids = set(outfit_update.item_ids) - existing_ids
        if invalid_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid clothing item IDs: {list(invalid_ids)}"
            )
        outfit.item_ids = outfit_update.item_ids

    db.commit()
    db.refresh(outfit)

    # Get full item details
    items = []
    if outfit.item_ids:
        db_items = db.query(ClothingItem).filter(
            ClothingItem.id.in_(outfit.item_ids)
        ).all()
        items = [ClothingItemResponse.model_validate(item) for item in db_items]

    return SavedOutfitResponse(
        id=outfit.id,
        name=outfit.name,
        description=outfit.description,
        item_ids=outfit.item_ids,
        items=items,
        created_at=outfit.created_at,
        updated_at=outfit.updated_at,
    )


@router.delete("/{outfit_id}")
async def delete_outfit(outfit_id: int, db: Session = Depends(get_db)):
    """Delete a saved outfit."""
    outfit = db.query(SavedOutfit).filter(SavedOutfit.id == outfit_id).first()
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")

    db.delete(outfit)
    db.commit()

    return {"message": "Outfit deleted successfully"}
