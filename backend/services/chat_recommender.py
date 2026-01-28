import anthropic
import json
import os
from typing import Optional
from sqlalchemy.orm import Session
from models import ClothingItem, OutfitChatMessage, ClothingItemNote
from services.weather import get_weather
from services.recommender import query_similar_items

# Initialize Anthropic client
claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def get_item_notes_context(db: Session, item_ids: list[int] = None) -> dict:
    """Get all notes for items, optionally filtered to specific IDs."""
    query = db.query(ClothingItemNote)
    if item_ids:
        query = query.filter(ClothingItemNote.item_id.in_(item_ids))

    notes = query.all()

    # Group notes by item_id
    notes_by_item = {}
    for note in notes:
        if note.item_id not in notes_by_item:
            notes_by_item[note.item_id] = []
        notes_by_item[note.item_id].append({
            "note": note.note,
            "type": note.note_type,
        })

    return notes_by_item


def get_conversation_history(db: Session, chat_id: int) -> list[dict]:
    """Get the conversation history for a chat."""
    messages = db.query(OutfitChatMessage).filter(
        OutfitChatMessage.chat_id == chat_id
    ).order_by(OutfitChatMessage.created_at).all()

    history = []
    for msg in messages:
        history.append({
            "role": msg.role,
            "content": msg.content,
        })

    return history


async def get_chat_response(
    db: Session,
    chat_id: int,
    user_message: str,
    event_type: Optional[str] = None,
    location: Optional[str] = None,
) -> tuple[str, list, list]:
    """
    Generate a chat response for outfit recommendations.

    Returns:
        tuple of (response_text, outfit_data, learned_notes)
        - response_text: The assistant's text response
        - outfit_data: List of outfit recommendations (if any)
        - learned_notes: List of notes learned about items from feedback
    """
    # Get weather if location provided
    weather_info = None
    if location:
        weather_info = await get_weather(location)

    # Get conversation history
    history = get_conversation_history(db, chat_id)

    # Get all wardrobe items
    all_items = db.query(ClothingItem).all()
    if not all_items:
        return (
            "I'd love to help you pick an outfit, but your wardrobe is empty! Add some clothes first.",
            [],
            []
        )

    # Get notes for all items
    notes_by_item = get_item_notes_context(db)

    # Format items for the prompt
    items_description = []
    for item in all_items:
        item_notes = notes_by_item.get(item.id, [])
        notes_text = ""
        if item_notes:
            notes_text = " USER NOTES: " + "; ".join([f"[{n['type']}] {n['note']}" for n in item_notes])

        items_description.append(
            f"- ID {item.id}: {item.name} ({item.category}/{item.subcategory}) - "
            f"{item.color}, {item.style} style, "
            f"good for {', '.join(item.occasion_suitability or ['casual'])} "
            f"in {', '.join(item.weather_suitability or ['any'])} weather"
            f"{notes_text}"
        )

    items_text = "\n".join(items_description)

    # Build weather context
    weather_context = ""
    if weather_info:
        weather_context = f"""
Current Weather:
- Location: {weather_info.get('location', 'Unknown')}
- Temperature: {weather_info.get('temperature', 'Unknown')}°F (feels like {weather_info.get('feels_like', 'Unknown')}°F)
- Conditions: {weather_info.get('description', 'Unknown')}
- Rain: {'Yes' if weather_info.get('is_rainy') else 'No'}
"""

    # Build the system prompt
    system_prompt = f"""You are a friendly, knowledgeable personal stylist AI helping users pick outfits from their wardrobe. You have a conversational style - you're helpful, warm, and give practical fashion advice.

YOUR CAPABILITIES:
1. Suggest complete outfits from the user's wardrobe
2. Understand and incorporate feedback about specific items (e.g., "those pants are too casual for work")
3. Learn user preferences and remember them during the conversation
4. Provide style tips and explain why certain combinations work

USER'S WARDROBE:
{items_text}

{weather_context}

IMPORTANT GUIDELINES:
1. Only suggest items from the wardrobe listed above - use the exact item IDs
2. When the user gives feedback about an item (e.g., "those pants don't work for beach weather"), acknowledge it and remember it
3. Create cohesive outfits that work together stylistically
4. Consider weather, occasion, and any user preferences
5. Be conversational but concise - don't be overly verbose

RESPONSE FORMAT:
When suggesting outfits, include them in a JSON block like this:
```json
{{
    "outfits": [
        {{
            "outfit_name": "Creative name",
            "item_ids": [1, 2, 3],
            "reasoning": "Why this works"
        }}
    ],
    "learned_notes": [
        {{
            "item_id": 5,
            "note": "User says these are better for beach, not formal occasions",
            "note_type": "occasion"
        }}
    ]
}}
```

The learned_notes should capture any feedback the user gives about specific items. Types can be: "weather", "occasion", "style", "fit", "general"

If you're just having a conversation without suggesting outfits, you can skip the JSON block entirely.

Remember: Be helpful and friendly! The user is asking you to be their personal stylist."""

    # Build messages for Claude
    messages = []

    # Add conversation history (skip for first message)
    for msg in history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Add current user message
    messages.append({
        "role": "user",
        "content": user_message
    })

    try:
        response = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
        )

        response_text = response.content[0].text

        # Parse out outfit data and learned notes if present
        outfit_data = []
        learned_notes = []

        if "```json" in response_text:
            try:
                json_match = response_text.split("```json")[1].split("```")[0]
                parsed = json.loads(json_match.strip())

                if "outfits" in parsed:
                    # Enrich outfit data with full item details
                    items_by_id = {item.id: item for item in all_items}
                    for outfit in parsed["outfits"]:
                        outfit_items = []
                        for item_id in outfit.get("item_ids", []):
                            if item_id in items_by_id:
                                outfit_items.append(items_by_id[item_id].to_dict())

                        if outfit_items:
                            outfit_data.append({
                                "outfit_name": outfit.get("outfit_name", "Outfit"),
                                "items": outfit_items,
                                "reasoning": outfit.get("reasoning", ""),
                            })

                if "learned_notes" in parsed:
                    # Validate that item_ids exist
                    valid_ids = {item.id for item in all_items}
                    for note in parsed["learned_notes"]:
                        if note.get("item_id") in valid_ids:
                            learned_notes.append({
                                "item_id": note["item_id"],
                                "note": note.get("note", ""),
                                "note_type": note.get("note_type", "general"),
                            })

                # Clean up response text - remove the JSON block for display
                clean_text = response_text.split("```json")[0].strip()
                if clean_text:
                    response_text = clean_text
                else:
                    # JSON was at the start, get text after it
                    parts = response_text.split("```")
                    if len(parts) > 2:
                        response_text = parts[2].strip()
                    else:
                        response_text = "Here are my outfit suggestions for you!"

            except (json.JSONDecodeError, IndexError, KeyError) as e:
                print(f"Error parsing JSON from response: {e}")
                # Keep original response text

        return response_text, outfit_data, learned_notes

    except Exception as e:
        print(f"Error getting chat response: {e}")
        return (
            f"I'm having trouble thinking right now. Could you try again? (Error: {str(e)})",
            [],
            []
        )
