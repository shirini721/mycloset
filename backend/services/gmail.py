import os
import json
import base64
import re
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
import httpx
import anthropic
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

# Initialize Anthropic client lazily
_anthropic_client = None


def get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            _anthropic_client = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client

# OAuth2 configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE = Path(__file__).parent.parent.parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent.parent.parent / "token.json"

# Common clothing retailer patterns
CLOTHING_RETAILERS = [
    "zara", "h&m", "hm.com", "uniqlo", "gap", "oldnavy", "banana republic",
    "nordstrom", "asos", "shein", "fashion nova", "revolve", "shopbop",
    "net-a-porter", "ssense", "farfetch", "mango", "pull&bear", "bershka",
    "massimo dutti", "cos", "service.cos.com", "arket", "& other stories", "everlane", "reformation",
    "free people", "anthropologie", "urban outfitters", "lululemon", "nike",
    "adidas", "puma", "new balance", "reebok", "under armour", "patagonia",
    "the north face", "columbia", "j.crew", "madewell", "express", "forever 21",
    "american eagle", "abercrombie", "hollister", "topshop", "boohoo", "missguided",
    "pretty little thing", "princess polly", "showpo", "beginning boutique",
    "amazon", "target", "walmart", "kohls", "macys", "bloomingdales", "saks",
    "neiman marcus", "bergdorf", "barneys", "selfridges", "harrods", "zalando",
    "fwrd", "mt.fwrd.com", "forward", "saksfifthavenue", "saks fifth avenue"
]


def get_oauth_flow(redirect_uri: str) -> Flow:
    """Create OAuth flow for Gmail authentication."""
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"Google credentials file not found at {CREDENTIALS_FILE}. "
            "Please download it from Google Cloud Console."
        )

    flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_FILE),
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    return flow


def get_auth_url(redirect_uri: str) -> str:
    """Get the Google OAuth authorization URL."""
    flow = get_oauth_flow(redirect_uri)
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    return auth_url


def exchange_code_for_token(code: str, redirect_uri: str) -> dict:
    """Exchange authorization code for tokens."""
    flow = get_oauth_flow(redirect_uri)
    flow.fetch_token(code=code)

    credentials = flow.credentials
    token_data = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes,
        'expiry': credentials.expiry.isoformat() if credentials.expiry else None
    }

    # Save token for future use
    with open(TOKEN_FILE, 'w') as f:
        json.dump(token_data, f)

    return token_data


def get_credentials() -> Optional[Credentials]:
    """Get valid credentials from stored token."""
    if not TOKEN_FILE.exists():
        return None

    with open(TOKEN_FILE, 'r') as f:
        token_data = json.load(f)

    credentials = Credentials(
        token=token_data.get('token'),
        refresh_token=token_data.get('refresh_token'),
        token_uri=token_data.get('token_uri'),
        client_id=token_data.get('client_id'),
        client_secret=token_data.get('client_secret'),
        scopes=token_data.get('scopes')
    )

    # Refresh if expired
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        # Update saved token
        token_data['token'] = credentials.token
        if credentials.expiry:
            token_data['expiry'] = credentials.expiry.isoformat()
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f)

    return credentials


def is_authenticated() -> bool:
    """Check if Gmail is authenticated."""
    creds = get_credentials()
    return creds is not None and creds.valid


def logout():
    """Remove stored credentials."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()


async def search_clothing_orders(
    days_back: int = 90,
    db: Session = None,
    include_seen: bool = False
) -> list[dict]:
    """
    Search Gmail for clothing order confirmations.
    Returns list of potential clothing orders with extracted info.

    - db: Database session for tracking processed emails
    - include_seen: If True, include previously processed emails
    """
    from models import ProcessedEmail

    credentials = get_credentials()
    if not credentials:
        raise ValueError("Not authenticated with Gmail")

    service = build('gmail', 'v1', credentials=credentials)

    # Build search query for order confirmations
    after_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')

    # Simple search for order-related emails - no attachment/image filter
    # since product images are embedded in HTML, not attachments
    query = f"after:{after_date} (subject:order OR subject:shipped OR subject:confirmation OR subject:receipt OR subject:\"thank you for shopping\" OR subject:\"thank you for your order\" OR subject:\"order details\")"

    print(f"[Gmail] Searching with query: {query}")

    # Get list of already processed email IDs
    seen_message_ids = set()
    if db and not include_seen:
        seen_emails = db.query(ProcessedEmail.message_id).all()
        seen_message_ids = {e.message_id for e in seen_emails}
        print(f"[Gmail] Excluding {len(seen_message_ids)} previously seen emails")

    try:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=100
        ).execute()

        messages = results.get('messages', [])
        print(f"[Gmail] Found {len(messages)} potential order emails")

        # Filter out already seen emails
        if seen_message_ids:
            messages = [m for m in messages if m['id'] not in seen_message_ids]
            print(f"[Gmail] {len(messages)} emails after filtering seen ones")

        orders = []
        for msg in messages:
            message_id = msg['id']
            order = await extract_order_info(service, message_id)

            # Mark email as processed in database
            if db:
                has_clothing = order is not None and bool(order.get('images'))
                processed_email = ProcessedEmail(
                    message_id=message_id,
                    subject=order.get('subject', '') if order else '',
                    retailer=order.get('retailer', '') if order else '',
                    has_clothing_images=has_clothing
                )
                try:
                    db.add(processed_email)
                    db.commit()
                except Exception as e:
                    db.rollback()
                    print(f"[Gmail] Error saving processed email: {e}")

            if order and order.get('images'):
                orders.append(order)

        print(f"[Gmail] Extracted {len(orders)} orders with images")
        return orders

    except Exception as e:
        print(f"[Gmail] Error searching emails: {e}")
        raise


async def extract_order_info(service, message_id: str) -> Optional[dict]:
    """Extract order information and product images from an email."""
    try:
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()

        headers = {h['name'].lower(): h['value'] for h in message['payload']['headers']}

        subject = headers.get('subject', '')
        from_email = headers.get('from', '')
        date = headers.get('date', '')

        # Get email body (HTML preferred)
        html_body = get_email_body(message['payload'], 'text/html')
        text_body = get_email_body(message['payload'], 'text/plain')

        body = html_body or text_body or ''

        # Extract potential product images from HTML
        images = []
        if html_body:
            images = extract_product_images(html_body, from_email)

        if not images:
            return None

        # Use AI to filter only actual clothing images
        print(f"[Gmail] Filtering {len(images)} images from: {subject[:50]}...")
        clothing_images = await filter_clothing_images(images)

        if not clothing_images:
            print(f"[Gmail] No clothing images found in: {subject[:50]}")
            return None

        # Identify retailer
        retailer = identify_retailer(from_email, subject)

        return {
            'message_id': message_id,
            'subject': subject,
            'from': from_email,
            'date': date,
            'retailer': retailer,
            'images': clothing_images
        }

    except Exception as e:
        print(f"[Gmail] Error extracting order {message_id}: {e}")
        return None


def get_email_body(payload: dict, mime_type: str) -> Optional[str]:
    """Extract email body of specified MIME type."""
    if payload.get('mimeType') == mime_type:
        data = payload.get('body', {}).get('data', '')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

    # Check parts
    for part in payload.get('parts', []):
        result = get_email_body(part, mime_type)
        if result:
            return result

    return None


def extract_product_images(html_content: str, from_email: str) -> list[dict]:
    """Extract product images from HTML email content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    images = []
    seen_urls = set()

    for img in soup.find_all('img'):
        src = img.get('src', '')
        alt = img.get('alt', '')

        # Skip if no source or already seen
        if not src or src in seen_urls:
            continue

        # Skip common non-product images
        skip_patterns = [
            'logo', 'icon', 'banner', 'header', 'footer', 'social',
            'facebook', 'twitter', 'instagram', 'pinterest', 'youtube',
            'spacer', 'pixel', 'tracking', '1x1', 'transparent',
            'email-open', 'unsubscribe', 'preference'
        ]

        src_lower = src.lower()
        alt_lower = alt.lower()

        if any(pattern in src_lower or pattern in alt_lower for pattern in skip_patterns):
            continue

        # Look for product-like images (larger dimensions, product keywords)
        width = img.get('width', '')
        height = img.get('height', '')

        # Try to get numeric dimensions
        try:
            w = int(re.sub(r'[^0-9]', '', str(width))) if width else 0
            h = int(re.sub(r'[^0-9]', '', str(height))) if height else 0
        except:
            w, h = 0, 0

        # Prefer images with reasonable dimensions or product-related alt text
        is_product_size = (w >= 100 and h >= 100) or (w == 0 and h == 0)  # Unknown size might be product
        has_product_alt = alt and len(alt) > 5 and not any(skip in alt_lower for skip in skip_patterns)

        if is_product_size or has_product_alt:
            seen_urls.add(src)
            images.append({
                'url': src,
                'alt': alt,
                'width': w,
                'height': h
            })

    # Sort by size (larger first) and limit
    images.sort(key=lambda x: (x['width'] * x['height']), reverse=True)
    return images[:10]  # Return top 10 images


def identify_retailer(from_email: str, subject: str) -> str:
    """Identify the retailer from email sender or subject."""
    from_lower = from_email.lower()
    subject_lower = subject.lower()

    for retailer in CLOTHING_RETAILERS:
        if retailer in from_lower or retailer in subject_lower:
            return retailer.title()

    # Try to extract domain
    match = re.search(r'@([a-zA-Z0-9.-]+)', from_email)
    if match:
        domain = match.group(1).replace('.com', '').replace('.co.uk', '')
        return domain.title()

    return "Unknown"


async def download_image(url: str, save_path: str) -> bool:
    """Download an image from URL and save it."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            with open(save_path, 'wb') as f:
                f.write(response.content)

            return True
    except Exception as e:
        print(f"[Gmail] Error downloading image {url}: {e}")
        return False


async def is_clothing_image(image_url: str) -> dict:
    """
    Use Claude Vision to determine if an image URL shows a clothing product.
    Returns dict with 'is_clothing' bool and 'description' if it is clothing.
    """
    client = get_anthropic_client()
    if not client:
        # If no API key, return True to not filter (fallback to old behavior)
        return {"is_clothing": True, "description": "", "name": ""}

    try:
        # Fetch the image
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as http_client:
            response = await http_client.get(image_url)
            response.raise_for_status()
            image_data = base64.standard_b64encode(response.content).decode("utf-8")

            # Determine media type from content-type header
            content_type = response.headers.get('content-type', 'image/jpeg')
            if 'png' in content_type:
                media_type = 'image/png'
            elif 'gif' in content_type:
                media_type = 'image/gif'
            elif 'webp' in content_type:
                media_type = 'image/webp'
            else:
                media_type = 'image/jpeg'

        # Ask Claude to analyze the image
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": """Is this image a clothing/fashion product photo (like a shirt, dress, pants, shoes, jacket, etc.)?

Answer in JSON format:
{
    "is_clothing": true/false,
    "name": "Brief name if clothing (e.g., 'Black Leather Jacket')",
    "reason": "Brief reason"
}

Return false for: icons, logos, banners, buttons, social media icons, decorative images, shipping graphics, payment icons, etc.
Return true only for: actual photos of clothing items, shoes, accessories that someone could wear."""
                        },
                    ],
                }
            ],
        )

        response_text = message.content[0].text

        # Parse JSON from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        result = json.loads(response_text.strip())
        return {
            "is_clothing": result.get("is_clothing", False),
            "name": result.get("name", ""),
            "reason": result.get("reason", "")
        }

    except Exception as e:
        print(f"[Gmail] Error checking if clothing image: {e}")
        # On error, include the image (don't filter it out)
        return {"is_clothing": True, "name": "", "reason": ""}


async def filter_clothing_images(images: list[dict]) -> list[dict]:
    """
    Filter a list of images to only include actual clothing products.
    Uses Claude Vision to analyze each image.
    """
    clothing_images = []

    for img in images[:8]:  # Limit to 8 images to avoid too many API calls
        result = await is_clothing_image(img['url'])

        if result.get('is_clothing'):
            img['ai_name'] = result.get('name', '')
            clothing_images.append(img)
            print(f"[Gmail] ✓ Clothing: {result.get('name', 'Unknown')}")
        else:
            print(f"[Gmail] ✗ Not clothing: {result.get('reason', 'Unknown')}")

    return clothing_images
