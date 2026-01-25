from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid
import aiofiles

from database import get_db
from schemas import ClothingItemResponse, ClothingItemUpdate
from services import clothing as clothing_service
from services.image_analyzer import analyze_clothing_image
from services.recommender import add_to_vector_store, remove_from_vector_store

router = APIRouter(prefix="/api/clothes", tags=["clothes"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("", response_model=list[ClothingItemResponse])
async def get_all_clothes(
    category: Optional[str] = None, db: Session = Depends(get_db)
):
    """Get all clothing items, optionally filtered by category."""
    items = clothing_service.get_all_clothes(db, category)
    return items


@router.get("/{item_id}", response_model=ClothingItemResponse)
async def get_clothing_item(item_id: int, db: Session = Depends(get_db)):
    """Get a single clothing item by ID."""
    item = clothing_service.get_clothing_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Clothing item not found")
    return item


@router.post("", response_model=ClothingItemResponse)
async def create_clothing_item(
    image: UploadFile = File(...),
    name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload a new clothing item with an image.
    The image will be analyzed by AI to extract attributes automatically.
    You can optionally provide a custom name.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if image.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}",
        )

    # Generate unique filename
    file_extension = os.path.splitext(image.filename)[1] or ".jpg"
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Save the uploaded file
    try:
        async with aiofiles.open(file_path, "wb") as f:
            content = await image.read()
            await f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")

    # Analyze the image with Claude Vision
    try:
        analysis = await analyze_clothing_image(file_path)
    except Exception as e:
        # If analysis fails, use defaults
        analysis = {
            "name": name or "Unknown Item",
            "category": "top",
            "subcategory": "unknown",
            "color": "unknown",
            "material": "unknown",
            "pattern": "solid",
            "style": "casual",
            "weather_suitability": ["mild"],
            "occasion_suitability": ["casual"],
            "description": f"Image analysis failed: {str(e)}",
        }

    # Override name if user provided one
    if name:
        analysis["name"] = name

    # Create the clothing item in the database
    item = clothing_service.create_clothing_item(
        db, analysis, image_path=f"/uploads/{unique_filename}"
    )

    # Add to vector store for RAG
    add_to_vector_store(item)

    return item


@router.put("/{item_id}", response_model=ClothingItemResponse)
async def update_clothing_item(
    item_id: int, update_data: ClothingItemUpdate, db: Session = Depends(get_db)
):
    """Update an existing clothing item's attributes."""
    item = clothing_service.update_clothing_item(db, item_id, update_data)
    if not item:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    # Update in vector store
    add_to_vector_store(item)

    return item


@router.delete("/{item_id}")
async def delete_clothing_item(item_id: int, db: Session = Depends(get_db)):
    """Delete a clothing item."""
    # Remove from vector store first
    remove_from_vector_store(item_id)

    success = clothing_service.delete_clothing_item(db, item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    return {"message": "Item deleted successfully"}


@router.get("/image/{filename}")
async def get_image(filename: str):
    """Serve an uploaded image."""
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path)
