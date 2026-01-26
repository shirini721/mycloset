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

# OAuth2 configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE = Path(__file__).parent.parent.parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent.parent.parent / "token.json"

# Common clothing retailer patterns
CLOTHING_RETAILERS = [
    "zara", "h&m", "hm.com", "uniqlo", "gap", "oldnavy", "banana republic",
    "nordstrom", "asos", "shein", "fashion nova", "revolve", "shopbop",
    "net-a-porter", "ssense", "farfetch", "mango", "pull&bear", "bershka",
    "massimo dutti", "cos", "arket", "& other stories", "everlane", "reformation",
    "free people", "anthropologie", "urban outfitters", "lululemon", "nike",
    "adidas", "puma", "new balance", "reebok", "under armour", "patagonia",
    "the north face", "columbia", "j.crew", "madewell", "express", "forever 21",
    "american eagle", "abercrombie", "hollister", "topshop", "boohoo", "missguided",
    "pretty little thing", "princess polly", "showpo", "beginning boutique",
    "amazon", "target", "walmart", "kohls", "macys", "bloomingdales", "saks",
    "neiman marcus", "bergdorf", "barneys", "selfridges", "harrods", "zalando"
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


async def search_clothing_orders(days_back: int = 90) -> list[dict]:
    """
    Search Gmail for clothing order confirmations.
    Returns list of potential clothing orders with extracted info.
    """
    credentials = get_credentials()
    if not credentials:
        raise ValueError("Not authenticated with Gmail")

    service = build('gmail', 'v1', credentials=credentials)

    # Build search query for order confirmations
    after_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')

    # Broader search - look for any order/receipt emails with images
    # Don't restrict to specific retailers
    query = f"(subject:order OR subject:confirmation OR subject:shipped OR subject:receipt OR subject:purchase OR subject:\"your order\" OR subject:\"order confirmed\") after:{after_date} has:attachment OR has:image"

    print(f"[Gmail] Searching with query: {query}")

    try:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=100
        ).execute()

        messages = results.get('messages', [])
        print(f"[Gmail] Found {len(messages)} potential order emails")

        orders = []
        for msg in messages:
            order = await extract_order_info(service, msg['id'])
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

        # Extract product images from HTML
        images = []
        if html_body:
            images = extract_product_images(html_body, from_email)

        if not images:
            return None

        # Identify retailer
        retailer = identify_retailer(from_email, subject)

        return {
            'message_id': message_id,
            'subject': subject,
            'from': from_email,
            'date': date,
            'retailer': retailer,
            'images': images
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
