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
    # Download to temp file first to get content type
    temp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.tmp")

    # Download the image
    result = await gmail_service.download_image(request.image_url, temp_path)
    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail="Failed to download image from email"
        )

    # Determine proper extension from content type
    content_type = result.get("content_type", "image/jpeg")
    ext_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }
    ext = ext_map.get(content_type.split(";")[0].strip(), ".jpg")

    # Rename to proper extension
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    os.rename(temp_path, file_path)

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
    days: str = "90",  # Can be "90" (days) or "4-5" (year range)
    include_seen: bool = False,
    db: Session = Depends(get_db)
):
    """
    Scan Gmail for order emails and stage images for review.
    No AI filtering - just extracts and stores images.

    days parameter can be:
    - A number like "90" meaning last 90 days
    - A range like "4-5" meaning 4-5 years ago
    - "5+" meaning 5+ years ago
    """
    if not gmail_service.is_authenticated():
        raise HTTPException(
            status_code=401,
            detail="Gmail not connected. Please authenticate first."
        )

    # Parse the days/range parameter
    from datetime import datetime, timedelta
    now = datetime.now()

    if "-" in days or days.endswith("+"):
        # It's a year range like "4-5" or "5+"
        if days == "0-1":
            after_date = now - timedelta(days=365)
            before_date = now
        elif days == "1-2":
            after_date = now - timedelta(days=730)
            before_date = now - timedelta(days=365)
        elif days == "2-3":
            after_date = now - timedelta(days=1095)
            before_date = now - timedelta(days=730)
        elif days == "3-4":
            after_date = now - timedelta(days=1460)
            before_date = now - timedelta(days=1095)
        elif days == "4-5":
            after_date = now - timedelta(days=1825)
            before_date = now - timedelta(days=1460)
        elif days == "5-6":
            after_date = now - timedelta(days=2190)
            before_date = now - timedelta(days=1825)
        elif days == "6-7":
            after_date = now - timedelta(days=2555)
            before_date = now - timedelta(days=2190)
        elif days == "5+":
            after_date = now - timedelta(days=3650)
            before_date = now - timedelta(days=1825)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid date range: {days}")

        try:
            result = await gmail_service.scan_and_stage_images_range(
                after_date=after_date,
                before_date=before_date,
                db=db,
                include_seen=include_seen
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # It's a simple days value
        days_int = min(int(days), 3650)

        try:
            result = await gmail_service.scan_and_stage_images(
                days_back=days_int,
                db=db,
                include_seen=include_seen
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


def parse_email_date(date_str: str):
    """Parse email date string to datetime object."""
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(date_str)
    except:
        return None


@router.get("/staged")
async def get_staged_images(
    status: str = "pending",
    retailer: str = None,
    date_range: str = None,  # "4-5" means 4-5 years ago
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get staged images for review, optionally filtered by retailer and date range."""
    query = db.query(StagedImage)

    if status != "all":
        query = query.filter(StagedImage.status == status)

    if retailer:
        query = query.filter(StagedImage.retailer == retailer)

    # Get all matching images first
    all_images = query.order_by(StagedImage.created_at.desc()).all()

    # Apply date range filter if specified
    if date_range:
        from datetime import datetime, timedelta
        now = datetime.now()

        if date_range == "0-1":
            min_date = now - timedelta(days=365)
            max_date = now
        elif date_range == "1-2":
            min_date = now - timedelta(days=730)
            max_date = now - timedelta(days=365)
        elif date_range == "2-3":
            min_date = now - timedelta(days=1095)
            max_date = now - timedelta(days=730)
        elif date_range == "3-4":
            min_date = now - timedelta(days=1460)
            max_date = now - timedelta(days=1095)
        elif date_range == "4-5":
            min_date = now - timedelta(days=1825)
            max_date = now - timedelta(days=1460)
        elif date_range == "5+":
            min_date = now - timedelta(days=3650)
            max_date = now - timedelta(days=1825)
        else:
            min_date = None
            max_date = None

        if min_date and max_date:
            filtered_images = []
            for img in all_images:
                if img.email_date:
                    email_dt = parse_email_date(img.email_date)
                    if email_dt and min_date <= email_dt.replace(tzinfo=None) <= max_date:
                        filtered_images.append(img)
            all_images = filtered_images

    total = len(all_images)
    images = all_images[offset:offset + limit]

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


@router.get("/staged/date-ranges")
async def get_date_range_stats(
    status: str = "pending",
    db: Session = Depends(get_db)
):
    """Get counts of staged images grouped by date range (years ago)."""
    from datetime import datetime, timedelta

    query = db.query(StagedImage)
    if status != "all":
        query = query.filter(StagedImage.status == status)

    all_images = query.all()
    now = datetime.now()

    # Define date ranges
    ranges = {
        "0-1": {"label": "Last year", "min": now - timedelta(days=365), "max": now, "count": 0},
        "1-2": {"label": "1-2 years ago", "min": now - timedelta(days=730), "max": now - timedelta(days=365), "count": 0},
        "2-3": {"label": "2-3 years ago", "min": now - timedelta(days=1095), "max": now - timedelta(days=730), "count": 0},
        "3-4": {"label": "3-4 years ago", "min": now - timedelta(days=1460), "max": now - timedelta(days=1095), "count": 0},
        "4-5": {"label": "4-5 years ago", "min": now - timedelta(days=1825), "max": now - timedelta(days=1460), "count": 0},
        "5+": {"label": "5+ years ago", "min": now - timedelta(days=3650), "max": now - timedelta(days=1825), "count": 0},
    }

    for img in all_images:
        if img.email_date:
            email_dt = parse_email_date(img.email_date)
            if email_dt:
                dt = email_dt.replace(tzinfo=None)
                for key, r in ranges.items():
                    if r["min"] <= dt <= r["max"]:
                        r["count"] += 1
                        break

    return {
        "date_ranges": [
            {"key": k, "label": v["label"], "count": v["count"]}
            for k, v in ranges.items()
            if v["count"] > 0  # Only return ranges with images
        ],
        "total": sum(r["count"] for r in ranges.values())
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


@router.post("/staged/cleanup-broken")
async def cleanup_broken_images(
    db: Session = Depends(get_db)
):
    """Check and remove staged images with broken/expired URLs."""
    import httpx

    pending_images = db.query(StagedImage).filter(
        StagedImage.status == "pending"
    ).all()

    broken_ids = []

    async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
        for img in pending_images:
            try:
                response = await client.head(img.image_url)
                if response.status_code >= 400:
                    broken_ids.append(img.id)
            except:
                broken_ids.append(img.id)

    # Mark broken images as rejected
    if broken_ids:
        db.query(StagedImage).filter(
            StagedImage.id.in_(broken_ids)
        ).update({"status": "rejected"}, synchronize_session=False)
        db.commit()

    return {
        "checked": len(pending_images),
        "broken": len(broken_ids),
        "broken_ids": broken_ids
    }


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

    # Download to temp file first to get content type
    temp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.tmp")

    # Download the image
    result = await gmail_service.download_image(image.image_url, temp_path)
    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail="Failed to download image"
        )

    # Determine proper extension from content type
    content_type = result.get("content_type", "image/jpeg")
    ext_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }
    ext = ext_map.get(content_type.split(";")[0].strip(), ".jpg")

    # Rename to proper extension
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    os.rename(temp_path, file_path)

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


@router.post("/staged/reset-by-date")
async def reset_staged_by_date_range(
    date_range: str,  # "4-5" means 4-5 years ago
    db: Session = Depends(get_db)
):
    """Reset staged images in a date range back to pending status AND clear their processed email records.

    This allows re-reviewing old images that were previously approved/rejected.
    """
    from datetime import datetime, timedelta
    from models import ProcessedEmail

    now = datetime.now()

    # Define date range
    if date_range == "0-1":
        min_date = now - timedelta(days=365)
        max_date = now
    elif date_range == "1-2":
        min_date = now - timedelta(days=730)
        max_date = now - timedelta(days=365)
    elif date_range == "2-3":
        min_date = now - timedelta(days=1095)
        max_date = now - timedelta(days=730)
    elif date_range == "3-4":
        min_date = now - timedelta(days=1460)
        max_date = now - timedelta(days=1095)
    elif date_range == "4-5":
        min_date = now - timedelta(days=1825)
        max_date = now - timedelta(days=1460)
    elif date_range == "5+":
        min_date = now - timedelta(days=3650)
        max_date = now - timedelta(days=1825)
    else:
        return {"error": "Invalid date range", "staged_reset": 0, "processed_cleared": 0}

    # Get all staged images and filter by email date
    all_staged = db.query(StagedImage).all()
    message_ids_to_clear = set()
    reset_count = 0

    for img in all_staged:
        if img.email_date:
            email_dt = parse_email_date(img.email_date)
            if email_dt and min_date <= email_dt.replace(tzinfo=None) <= max_date:
                # Delete this staged image so it can be re-scanned fresh
                message_ids_to_clear.add(img.message_id)
                db.delete(img)
                reset_count += 1

    # Clear processed email records for these message IDs
    processed_cleared = 0
    if message_ids_to_clear:
        processed_cleared = db.query(ProcessedEmail).filter(
            ProcessedEmail.message_id.in_(message_ids_to_clear)
        ).delete(synchronize_session=False)

    db.commit()
    return {
        "staged_deleted": reset_count,
        "processed_cleared": processed_cleared,
        "date_range": date_range
    }
