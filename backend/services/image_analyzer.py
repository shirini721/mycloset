import anthropic
import base64
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Initialize client lazily
_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                f"ANTHROPIC_API_KEY not found. Please set it in your .env file at {env_path}"
            )
        print(f"[ImageAnalyzer] Initializing Anthropic client...")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


ANALYSIS_PROMPT = """Analyze this clothing item image and extract detailed information about it.

Return a JSON object with the following structure:
{
    "name": "A descriptive name for the item (e.g., 'Navy Blue Oxford Shirt')",
    "category": "One of: top, bottom, shoes, outerwear, accessory, dress, activewear",
    "subcategory": "Specific type (e.g., 't-shirt', 'jeans', 'sneakers', 'blazer', 'scarf', 'maxi dress')",
    "color": "Primary color(s) of the item",
    "material": "Estimated material (e.g., 'cotton', 'denim', 'leather', 'wool', 'polyester')",
    "pattern": "One of: solid, striped, plaid, floral, geometric, abstract, animal print, polka dot, other",
    "style": "One of: casual, formal, business casual, sporty, bohemian, elegant, streetwear, preppy, minimalist",
    "weather_suitability": ["Array of suitable weather conditions: hot, warm, mild, cool, cold, rainy"],
    "occasion_suitability": ["Array of suitable occasions: casual, work, formal, party, date, workout, outdoor, beach, wedding"],
    "description": "A brief 1-2 sentence description of the item, including notable features, fit suggestions, and styling potential"
}

Be accurate and detailed. If something is unclear, make your best educated guess based on the visual appearance.
Return ONLY the JSON object, no additional text."""


async def analyze_clothing_image(image_path: str) -> dict:
    """
    Analyze a clothing image using Claude Vision API.
    Returns extracted attributes as a dictionary.
    """
    print(f"[ImageAnalyzer] Analyzing image: {image_path}")

    # Read and encode the image
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Determine media type
    suffix = image_path.suffix.lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(suffix, "image/jpeg")
    print(f"[ImageAnalyzer] Media type: {media_type}")

    # Read and base64 encode the image
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    print(f"[ImageAnalyzer] Image encoded, size: {len(image_data)} chars")

    # Get the client (lazy initialization)
    client = get_client()
    print("[ImageAnalyzer] Calling Claude Vision API...")

    # Call Claude Vision API
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
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
                        "text": ANALYSIS_PROMPT,
                    },
                ],
            }
        ],
    )

    # Parse the response
    response_text = message.content[0].text
    print(f"[ImageAnalyzer] Got response: {response_text[:200]}...")

    # Try to extract JSON from the response
    try:
        # Handle case where response might have markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        result = json.loads(response_text.strip())
        print(f"[ImageAnalyzer] Successfully parsed: {result.get('name')}")
        return result
    except json.JSONDecodeError as e:
        print(f"[ImageAnalyzer] JSON parse error: {e}")
        print(f"[ImageAnalyzer] Raw response: {response_text}")
        # Return a basic structure if parsing fails
        return {
            "name": "Unknown Item",
            "category": "top",
            "subcategory": "unknown",
            "color": "unknown",
            "material": "unknown",
            "pattern": "solid",
            "style": "casual",
            "weather_suitability": ["mild"],
            "occasion_suitability": ["casual"],
            "description": f"Image analysis failed to parse: {str(e)}",
        }
