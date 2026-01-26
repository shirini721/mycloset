from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os
import uuid

from database import get_db
from services import gmail as gmail_service
from services.image_analyzer import analyze_clothing_image
from services.clothing import create_clothing_item
from services.recommender import add_to_vector_store

router = APIRouter(prefix="/api/gmail", tags=["gmail"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "uploads")


class ImportRequest(BaseModel):
    image_url: str
    suggested_name: Optional[str] = None


@router.get("/status")
async def get_gmail_status():
    """Check if Gmail is connected."""
    try:
        is_auth = gmail_service.is_authenticated()
        return {
            "connected": is_auth,
            "credentials_configured": gmail_service.CREDENTIALS_FILE.exists()
        }
    except Exception as e:
        return {
            "connected": False,
            "credentials_configured": False,
            "error": str(e)
        }


@router.get("/auth")
async def start_gmail_auth(request: Request):
    """Start Gmail OAuth flow."""
    if not gmail_service.CREDENTIALS_FILE.exists():
        raise HTTPException(
            status_code=400,
            detail="Google credentials not configured. Please add credentials.json to the project root."
        )

    # Build redirect URI
    redirect_uri = str(request.url_for('gmail_callback'))

    try:
        auth_url = gmail_service.get_auth_url(redirect_uri)
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/callback")
async def gmail_callback(request: Request, code: str = None, error: str = None):
    """Handle OAuth callback from Google."""
    if error:
        # Redirect to frontend with error
        return RedirectResponse(url=f"/?gmail_error={error}")

    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided")

    redirect_uri = str(request.url_for('gmail_callback'))

    try:
        gmail_service.exchange_code_for_token(code, redirect_uri)
        # Redirect to frontend with success
        return RedirectResponse(url="/?gmail_connected=true")
    except Exception as e:
        return RedirectResponse(url=f"/?gmail_error={str(e)}")


@router.post("/disconnect")
async def disconnect_gmail():
    """Disconnect Gmail account."""
    gmail_service.logout()
    return {"message": "Gmail disconnected successfully"}


@router.get("/orders")
async def get_clothing_orders(
    days: int = 90,
    include_seen: bool = False,
    db: Session = Depends(get_db)
):
    """
    Search Gmail for clothing order confirmations.
    Returns list of orders with product images.

    - days: Number of days to search back (max 1825 = 5 years)
    - include_seen: If True, include previously processed emails
    """
    if not gmail_service.is_authenticated():
        raise HTTPException(
            status_code=401,
            detail="Gmail not connected. Please authenticate first."
        )

    # Cap at 5 years
    days = min(days, 1825)

    try:
        orders = await gmail_service.search_clothing_orders(
            days_back=days,
            db=db,
            include_seen=include_seen
        )
        return {"orders": orders, "count": len(orders)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import")
async def import_from_email(
    request: ImportRequest,
    db: Session = Depends(get_db)
):
    """
    Import a clothing item from an email image URL.
    Downloads the image, analyzes it, and adds to wardrobe.
    """
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}.jpg"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Download the image
    success = await gmail_service.download_image(request.image_url, file_path)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to download image from email"
        )

    # Analyze the image
    try:
        analysis = await analyze_clothing_image(file_path)
    except Exception as e:
        # Clean up downloaded file on error
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze image: {str(e)}"
        )

    # Override name if provided
    if request.suggested_name:
        analysis["name"] = request.suggested_name

    # Create the clothing item
    item = create_clothing_item(
        db, analysis, image_path=f"/uploads/{unique_filename}"
    )

    # Add to vector store
    add_to_vector_store(item)

    return {
        "message": "Item imported successfully",
        "item": item.to_dict()
    }
