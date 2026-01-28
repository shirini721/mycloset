from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from database import get_db
from models import OutfitChat, OutfitChatMessage, ClothingItem, ClothingItemNote
from schemas import (
    OutfitChatCreate,
    OutfitChatMessageCreate,
    OutfitChatResponse,
    OutfitChatListResponse,
    OutfitChatMessageResponse,
    ClothingItemNoteCreate,
    ClothingItemNoteResponse,
)
from services.chat_recommender import get_chat_response

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("", response_model=list[OutfitChatListResponse])
async def list_chats(limit: int = 20, db: Session = Depends(get_db)):
    """List recent outfit chats."""
    chats = db.query(OutfitChat).order_by(OutfitChat.created_at.desc()).limit(limit).all()

    result = []
    for chat in chats:
        msg_count = db.query(OutfitChatMessage).filter(OutfitChatMessage.chat_id == chat.id).count()
        result.append(OutfitChatListResponse(
            id=chat.id,
            title=chat.title,
            event_type=chat.event_type,
            created_at=chat.created_at,
            message_count=msg_count
        ))

    return result


@router.post("", response_model=OutfitChatResponse)
async def create_chat(request: OutfitChatCreate, db: Session = Depends(get_db)):
    """Create a new outfit chat and get initial response."""
    # Create the chat
    chat = OutfitChat(
        title=f"Outfit for {request.event_type or 'any occasion'}",
        event_type=request.event_type,
        location=request.location,
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)

    # Create the user message
    user_message = OutfitChatMessage(
        chat_id=chat.id,
        role="user",
        content=request.initial_message,
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # Get AI response
    assistant_content, outfit_data, learned_notes = await get_chat_response(
        db=db,
        chat_id=chat.id,
        user_message=request.initial_message,
        event_type=request.event_type,
        location=request.location,
    )

    # Save assistant message
    assistant_message = OutfitChatMessage(
        chat_id=chat.id,
        role="assistant",
        content=assistant_content,
        outfit_data=outfit_data,
    )
    db.add(assistant_message)

    # Save any learned notes about items
    for note_data in learned_notes:
        note = ClothingItemNote(
            item_id=note_data["item_id"],
            note=note_data["note"],
            note_type=note_data.get("note_type", "general"),
            source="chat",
            chat_id=chat.id,
        )
        db.add(note)

    db.commit()
    db.refresh(assistant_message)

    # Return full chat with messages
    messages = db.query(OutfitChatMessage).filter(
        OutfitChatMessage.chat_id == chat.id
    ).order_by(OutfitChatMessage.created_at).all()

    return OutfitChatResponse(
        id=chat.id,
        title=chat.title,
        event_type=chat.event_type,
        location=chat.location,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        messages=[OutfitChatMessageResponse(
            id=m.id,
            chat_id=m.chat_id,
            role=m.role,
            content=m.content,
            outfit_data=m.outfit_data,
            created_at=m.created_at,
        ) for m in messages]
    )


@router.get("/{chat_id}", response_model=OutfitChatResponse)
async def get_chat(chat_id: int, db: Session = Depends(get_db)):
    """Get a specific chat with all messages."""
    chat = db.query(OutfitChat).filter(OutfitChat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages = db.query(OutfitChatMessage).filter(
        OutfitChatMessage.chat_id == chat_id
    ).order_by(OutfitChatMessage.created_at).all()

    return OutfitChatResponse(
        id=chat.id,
        title=chat.title,
        event_type=chat.event_type,
        location=chat.location,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        messages=[OutfitChatMessageResponse(
            id=m.id,
            chat_id=m.chat_id,
            role=m.role,
            content=m.content,
            outfit_data=m.outfit_data,
            created_at=m.created_at,
        ) for m in messages]
    )


@router.post("/{chat_id}/message", response_model=OutfitChatResponse)
async def send_message(
    chat_id: int,
    request: OutfitChatMessageCreate,
    db: Session = Depends(get_db)
):
    """Send a message in an existing chat and get AI response."""
    chat = db.query(OutfitChat).filter(OutfitChat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Create the user message
    user_message = OutfitChatMessage(
        chat_id=chat_id,
        role="user",
        content=request.content,
    )
    db.add(user_message)
    db.commit()

    # Get AI response with conversation context
    assistant_content, outfit_data, learned_notes = await get_chat_response(
        db=db,
        chat_id=chat_id,
        user_message=request.content,
        event_type=chat.event_type,
        location=chat.location,
    )

    # Save assistant message
    assistant_message = OutfitChatMessage(
        chat_id=chat_id,
        role="assistant",
        content=assistant_content,
        outfit_data=outfit_data,
    )
    db.add(assistant_message)

    # Save any learned notes about items
    for note_data in learned_notes:
        note = ClothingItemNote(
            item_id=note_data["item_id"],
            note=note_data["note"],
            note_type=note_data.get("note_type", "general"),
            source="chat",
            chat_id=chat_id,
        )
        db.add(note)

    # Update chat timestamp
    chat.updated_at = func.now()
    db.commit()

    # Return full chat with messages
    messages = db.query(OutfitChatMessage).filter(
        OutfitChatMessage.chat_id == chat_id
    ).order_by(OutfitChatMessage.created_at).all()

    return OutfitChatResponse(
        id=chat.id,
        title=chat.title,
        event_type=chat.event_type,
        location=chat.location,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        messages=[OutfitChatMessageResponse(
            id=m.id,
            chat_id=m.chat_id,
            role=m.role,
            content=m.content,
            outfit_data=m.outfit_data,
            created_at=m.created_at,
        ) for m in messages]
    )


@router.delete("/{chat_id}")
async def delete_chat(chat_id: int, db: Session = Depends(get_db)):
    """Delete a chat and its messages."""
    chat = db.query(OutfitChat).filter(OutfitChat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Delete messages first
    db.query(OutfitChatMessage).filter(OutfitChatMessage.chat_id == chat_id).delete()
    # Delete chat
    db.delete(chat)
    db.commit()

    return {"message": "Chat deleted successfully"}


# Item notes endpoints
@router.get("/items/{item_id}/notes", response_model=list[ClothingItemNoteResponse])
async def get_item_notes(item_id: int, db: Session = Depends(get_db)):
    """Get all notes for a clothing item."""
    item = db.query(ClothingItem).filter(ClothingItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    notes = db.query(ClothingItemNote).filter(
        ClothingItemNote.item_id == item_id
    ).order_by(ClothingItemNote.created_at.desc()).all()

    return [ClothingItemNoteResponse(
        id=n.id,
        item_id=n.item_id,
        note=n.note,
        note_type=n.note_type,
        source=n.source,
        created_at=n.created_at,
    ) for n in notes]


@router.post("/items/{item_id}/notes", response_model=ClothingItemNoteResponse)
async def add_item_note(
    item_id: int,
    request: ClothingItemNoteCreate,
    db: Session = Depends(get_db)
):
    """Add a manual note to a clothing item."""
    item = db.query(ClothingItem).filter(ClothingItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    note = ClothingItemNote(
        item_id=item_id,
        note=request.note,
        note_type=request.note_type,
        source="manual",
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return ClothingItemNoteResponse(
        id=note.id,
        item_id=note.item_id,
        note=note.note,
        note_type=note.note_type,
        source=note.source,
        created_at=note.created_at,
    )


@router.delete("/items/notes/{note_id}")
async def delete_item_note(note_id: int, db: Session = Depends(get_db)):
    """Delete a note from a clothing item."""
    note = db.query(ClothingItemNote).filter(ClothingItemNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    db.delete(note)
    db.commit()

    return {"message": "Note deleted successfully"}
