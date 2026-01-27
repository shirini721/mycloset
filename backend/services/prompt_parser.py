import anthropic
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
        print(f"[PromptParser] Initializing Anthropic client...")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


PARSE_PROMPT = """You are a wardrobe assistant. A user is describing a clothing item they own or want to add to their wardrobe using natural language.

Parse their description and extract the following attributes:

{
    "name": "A descriptive name for the item (e.g., 'Navy Blue Oxford Shirt')",
    "category": "One of: top, bottom, shoes, outerwear, accessory, dress, activewear",
    "subcategory": "Specific type (e.g., 't-shirt', 'jeans', 'sneakers', 'blazer', 'scarf', 'maxi dress')",
    "color": "Primary color(s) of the item",
    "material": "Material if mentioned (e.g., 'cotton', 'denim', 'leather', 'wool', 'polyester'), or your best guess",
    "pattern": "One of: solid, striped, plaid, floral, geometric, abstract, animal print, polka dot, other",
    "style": "One of: casual, formal, business casual, sporty, bohemian, elegant, streetwear, preppy, minimalist",
    "weather_suitability": ["Array of suitable weather conditions: hot, warm, mild, cool, cold, rainy"],
    "occasion_suitability": ["Array of suitable occasions: casual, work, formal, party, date, workout, outdoor, beach, wedding"],
    "description": "A brief 1-2 sentence description of the item based on user's description"
}

User's description: {user_prompt}

Be helpful and infer reasonable defaults for anything not explicitly mentioned. Make the name descriptive and specific.
Return ONLY the JSON object, no additional text."""


async def parse_clothing_prompt(user_prompt: str) -> dict:
    """
    Parse a natural language description of a clothing item using Claude.
    Returns extracted attributes as a dictionary.
    """
    print(f"[PromptParser] Parsing prompt: {user_prompt}")

    # Get the client (lazy initialization)
    client = get_client()
    print("[PromptParser] Calling Claude API...")

    # Call Claude API
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": PARSE_PROMPT.format(user_prompt=user_prompt),
            }
        ],
    )

    # Parse the response
    response_text = message.content[0].text
    print(f"[PromptParser] Got response: {response_text[:200]}...")

    # Try to extract JSON from the response
    try:
        # Handle case where response might have markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        result = json.loads(response_text.strip())
        print(f"[PromptParser] Successfully parsed: {result.get('name')}")
        return result
    except json.JSONDecodeError as e:
        print(f"[PromptParser] JSON parse error: {e}")
        print(f"[PromptParser] Raw response: {response_text}")
        # Return a basic structure if parsing fails
        return {
            "name": user_prompt[:50] if len(user_prompt) > 50 else user_prompt,
            "category": "top",
            "subcategory": "unknown",
            "color": "unknown",
            "material": "unknown",
            "pattern": "solid",
            "style": "casual",
            "weather_suitability": ["mild"],
            "occasion_suitability": ["casual"],
            "description": user_prompt,
        }
