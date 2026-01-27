from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import os
import uuid

from database import get_db
from models import StagedImage
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

    # Cap at 10 years
    days = min(days, 3650)

    try:
        orders = await gmail_service.search_clothing_orders(
            days_back=days,
            db=db,
            include_seen=include_seen
        )
        return {"orders": orders, "count": len(orders)}
    except gmail_service.RateLimitError as e:
        # Return partial results with a rate limit indicator
        return {
            "orders": e.partial_results,
            "count": len(e.partial_results),
            "rate_limited": True,
            "error": str(e)
        }
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


@router.post("/scan")
async def scan_emails(
    days: int = 90,
    include_seen: bool = False,
    db: Session = Depends(get_db)
):
    """
    Scan Gmail for order emails and stage images for review.
    No AI filtering - just extracts and stores images.
    """
    if not gmail_service.is_authenticated():
        raise HTTPException(
            status_code=401,
            detail="Gmail not connected. Please authenticate first."
        )

    # Cap at 10 years
    days = min(days, 3650)

    try:
        result = await gmail_service.scan_and_stage_images(
            days_back=days,
            db=db,
            include_seen=include_seen
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staged")
async def get_staged_images(
    status: str = "pending",
    retailer: str = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get staged images for review, optionally filtered by retailer."""
    query = db.query(StagedImage)

    if status != "all":
        query = query.filter(StagedImage.status == status)

    if retailer:
        query = query.filter(StagedImage.retailer == retailer)

    total = query.count()
    images = query.order_by(StagedImage.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "images": [img.to_dict() for img in images],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/staged/retailers")
async def get_retailer_stats(
    status: str = "pending",
    db: Session = Depends(get_db)
):
    """Get counts of staged images grouped by retailer."""
    from sqlalchemy import func

    query = db.query(
        StagedImage.retailer,
        func.count(StagedImage.id).label('count')
    )

    if status != "all":
        query = query.filter(StagedImage.status == status)

    results = query.group_by(StagedImage.retailer).order_by(func.count(StagedImage.id).desc()).all()

    return {
        "retailers": [{"name": r[0] or "Unknown", "count": r[1]} for r in results],
        "total": sum(r[1] for r in results)
    }


@router.post("/staged/reject-retailer")
async def reject_by_retailer(
    retailer: str,
    db: Session = Depends(get_db)
):
    """Reject all pending images from a specific retailer."""
    updated = db.query(StagedImage).filter(
        StagedImage.retailer == retailer,
        StagedImage.status == "pending"
    ).update({"status": "rejected"})

    db.commit()
    return {"rejected": updated, "retailer": retailer}


@router.post("/staged/reject-all")
async def reject_all_pending(
    db: Session = Depends(get_db)
):
    """Reject ALL pending images. Use after cherry-picking what you want to keep."""
    updated = db.query(StagedImage).filter(
        StagedImage.status == "pending"
    ).update({"status": "rejected"})

    db.commit()
    return {"rejected": updated}


class StagedImageAction(BaseModel):
    image_ids: List[int]
    action: str  # "approve" or "reject"


@router.post("/staged/action")
async def update_staged_images(
    request: StagedImageAction,
    db: Session = Depends(get_db)
):
    """Approve or reject staged images."""
    if request.action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")

    updated = 0
    for image_id in request.image_ids:
        image = db.query(StagedImage).filter(StagedImage.id == image_id).first()
        if image:
            image.status = "approved" if request.action == "approve" else "rejected"
            updated += 1

    db.commit()
    return {"updated": updated, "action": request.action}


@router.post("/staged/{image_id}/import")
async def import_staged_image(
    image_id: int,
    db: Session = Depends(get_db)
):
    """
    Import a staged image to the wardrobe.
    Downloads, analyzes with AI, and adds to wardrobe.
    """
    image = db.query(StagedImage).filter(StagedImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Staged image not found")

    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}.jpg"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Download the image
    success = await gmail_service.download_image(image.image_url, file_path)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to download image"
        )

    # Analyze the image
    try:
        analysis = await analyze_clothing_image(file_path)
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze image: {str(e)}"
        )

    # Create the clothing item
    item = create_clothing_item(
        db, analysis, image_path=f"/uploads/{unique_filename}"
    )

    # Add to vector store
    add_to_vector_store(item)

    # Mark staged image as approved
    image.status = "approved"
    db.commit()

    return {
        "message": "Item imported successfully",
        "item": item.to_dict()
    }


@router.delete("/staged/clear")
async def clear_staged_images(
    status: str = "rejected",
    clear_processed: bool = False,
    db: Session = Depends(get_db)
):
    """Clear staged images by status (default: rejected).

    If clear_processed=True, also clears processed_emails to allow full rescan.
    """
    from models import ProcessedEmail

    if status == "all":
        deleted = db.query(StagedImage).delete()
    else:
        deleted = db.query(StagedImage).filter(StagedImage.status == status).delete()

    processed_deleted = 0
    if clear_processed:
        processed_deleted = db.query(ProcessedEmail).delete()

    db.commit()
    return {"deleted": deleted, "processed_cleared": processed_deleted}
