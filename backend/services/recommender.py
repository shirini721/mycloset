import chromadb
from chromadb.config import Settings
import anthropic
import json
import os
from typing import Optional
from sqlalchemy.orm import Session
from models import ClothingItem
from services.clothing import search_clothes

# Initialize ChromaDB client
chroma_client = chromadb.Client(Settings(anonymized_telemetry=False))

# Create or get the collection for clothing embeddings
try:
    clothing_collection = chroma_client.get_or_create_collection(
        name="clothing_items",
        metadata={"description": "Embeddings for wardrobe items"},
    )
except Exception:
    clothing_collection = chroma_client.create_collection(
        name="clothing_items",
        metadata={"description": "Embeddings for wardrobe items"},
    )

# Initialize Anthropic client
claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def add_to_vector_store(item: ClothingItem):
    """Add a clothing item to the vector store for RAG retrieval."""
    # Create a rich text description for embedding
    text = f"""
    {item.name}: A {item.color} {item.subcategory or item.category} made of {item.material or 'unknown material'}.
    Style: {item.style or 'casual'}. Pattern: {item.pattern or 'solid'}.
    Good for weather: {', '.join(item.weather_suitability or ['any'])}.
    Suitable occasions: {', '.join(item.occasion_suitability or ['casual'])}.
    {item.description or ''}
    """.strip()

    # Add to ChromaDB (it will generate embeddings automatically)
    clothing_collection.upsert(
        ids=[str(item.id)],
        documents=[text],
        metadatas=[
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "subcategory": item.subcategory or "",
                "color": item.color or "",
                "style": item.style or "",
                "weather": ",".join(item.weather_suitability or []),
                "occasion": ",".join(item.occasion_suitability or []),
            }
        ],
    )


def remove_from_vector_store(item_id: int):
    """Remove a clothing item from the vector store."""
    try:
        clothing_collection.delete(ids=[str(item_id)])
    except Exception:
        pass


def query_similar_items(query: str, n_results: int = 20) -> list[dict]:
    """Query the vector store for similar items."""
    try:
        results = clothing_collection.query(query_texts=[query], n_results=n_results)
        if results and results["metadatas"]:
            return results["metadatas"][0]
        return []
    except Exception as e:
        print(f"Error querying vector store: {e}")
        return []


async def get_outfit_recommendations(
    db: Session,
    weather_info: dict,
    event_type: str,
    additional_preferences: Optional[str] = None,
) -> list[dict]:
    """
    Generate outfit recommendations using RAG + Claude.

    1. Use weather and event to query ChromaDB for relevant items
    2. Get candidate items from the database
    3. Use Claude to create cohesive outfit combinations
    """
    # Build a query for RAG retrieval
    weather_category = weather_info.get("weather_category", ["mild"])
    temp = weather_info.get("temperature", 70)
    is_rainy = weather_info.get("is_rainy", False)

    query = f"""
    Looking for an outfit for a {event_type} event.
    Weather: {weather_info.get('description', 'mild')}, {temp}°F.
    Need clothes suitable for {', '.join(weather_category)} weather.
    {"Need something rain-appropriate." if is_rainy else ""}
    {additional_preferences or ""}
    """

    # Query vector store for relevant items
    similar_items_meta = query_similar_items(query, n_results=30)
    relevant_ids = [m["id"] for m in similar_items_meta if "id" in m]

    # Also get items from traditional filtering as backup
    filtered_items = search_clothes(
        db, weather=weather_category, occasion=[event_type.lower()]
    )

    # Combine IDs
    all_ids = set(relevant_ids + [item.id for item in filtered_items])

    # Fetch full item details from database
    all_items = db.query(ClothingItem).filter(ClothingItem.id.in_(all_ids)).all()

    if not all_items:
        # If no matches, get all items and let Claude figure it out
        all_items = db.query(ClothingItem).all()

    if not all_items:
        return []

    # Format items for Claude
    items_description = "\n".join(
        [
            f"- ID {item.id}: {item.name} ({item.category}/{item.subcategory}) - {item.color}, {item.style} style, "
            f"good for {', '.join(item.occasion_suitability or ['casual'])} "
            f"in {', '.join(item.weather_suitability or ['any'])} weather"
            for item in all_items
        ]
    )

    # Use Claude to generate outfit recommendations
    prompt = f"""You are a personal stylist AI. Based on the user's wardrobe and the context, create 3 complete outfit recommendations.

CONTEXT:
- Event type: {event_type}
- Weather: {weather_info.get('description', 'Unknown')}, {temp}°F, feels like {weather_info.get('feels_like', temp)}°F
- Location: {weather_info.get('location', 'Unknown')}
- {"It's rainy - consider water-resistant options" if is_rainy else "No rain expected"}
{f"- User preferences: {additional_preferences}" if additional_preferences else ""}

AVAILABLE WARDROBE ITEMS:
{items_description}

Create 3 outfit recommendations. Each outfit should:
1. Be appropriate for the weather and event
2. Be stylistically cohesive
3. Include items from different categories (top, bottom, shoes, etc.)
4. Only use items from the available wardrobe (reference by ID)

Return your response as a JSON array with exactly this structure:
[
  {{
    "outfit_name": "Creative name for this outfit",
    "item_ids": [1, 2, 3],
    "reasoning": "Why this outfit works for the occasion and weather",
    "style_notes": "Tips for wearing this outfit"
  }}
]

Only return the JSON array, no other text."""

    try:
        response = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text

        # Parse JSON from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        recommendations_raw = json.loads(response_text.strip())

        # Build full recommendation objects with item details
        recommendations = []
        items_by_id = {item.id: item for item in all_items}

        for rec in recommendations_raw:
            outfit_items = [
                items_by_id[item_id].to_dict()
                for item_id in rec.get("item_ids", [])
                if item_id in items_by_id
            ]

            if outfit_items:  # Only include if we have valid items
                recommendations.append(
                    {
                        "outfit_name": rec.get("outfit_name", "Outfit"),
                        "items": outfit_items,
                        "reasoning": rec.get("reasoning", ""),
                        "style_notes": rec.get("style_notes", ""),
                    }
                )

        return recommendations

    except Exception as e:
        print(f"Error generating recommendations: {e}")
        return []


def rebuild_vector_store(db: Session):
    """Rebuild the entire vector store from database items."""
    # Clear existing
    try:
        chroma_client.delete_collection("clothing_items")
    except Exception:
        pass

    global clothing_collection
    clothing_collection = chroma_client.create_collection(
        name="clothing_items",
        metadata={"description": "Embeddings for wardrobe items"},
    )

    # Add all items
    all_items = db.query(ClothingItem).all()
    for item in all_items:
        add_to_vector_store(item)

    return len(all_items)
