from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import uuid
from openai import OpenAI
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import text

from .safety import SafetyRouter
from .database import get_db, init_db
from .models import Session, SafetyIntervention, SafetyCategory
from . import prompts

app = FastAPI(title="Life Story Chatbot API")

# Add CORS middleware - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=False,  # Set to False when using allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
openai_client = None
if os.getenv("OPENAI_API_KEY"):
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize safety router
safety_router = SafetyRouter()

# Summary generation frequency (every N messages)
SUMMARY_FREQUENCY = 4


@app.on_event("startup")
def on_startup():
    """Initialize database tables on startup."""
    init_db()
    print("Database initialized")

class ChatIn(BaseModel):
    session_id: str
    message: str

class ChatOut(BaseModel):
    session_id: str
    reply: str
    has_summary: bool = False

class SessionOut(BaseModel):
    session_id: str
    message_count: int
    summary: Optional[str] = None
    created_at: str
    updated_at: str


def get_or_create_session(db: DBSession, session_id: str) -> Session:
    """Load existing session or create a new one."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        # Invalid UUID, create new one
        session_uuid = uuid.uuid4()

    session = db.query(Session).filter(Session.id == session_uuid).first()

    if not session:
        session = Session(id=session_uuid)
        db.add(session)
        db.commit()
        db.refresh(session)

    return session


def generate_summary(existing_summary: Optional[str], user_message: str, assistant_reply: str) -> str:
    """
    Generate an updated conversation summary using the LLM.

    Takes the existing summary and recent exchange to create an updated summary
    that captures key themes, memories, and preferences mentioned.
    """
    if not openai_client:
        return existing_summary or ""

    summary_prompt = prompts.get_prompt("summary", "system")

    if existing_summary:
        context = prompts.render_prompt(
            "summary", "update",
            existing_summary=existing_summary,
            user_message=user_message,
            assistant_reply=assistant_reply,
        )
    else:
        context = prompts.render_prompt(
            "summary", "initial",
            user_message=user_message,
            assistant_reply=assistant_reply,
        )

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": summary_prompt},
                {"role": "user", "content": context}
            ],
            max_tokens=200,
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Summary generation error: {e}")
        return existing_summary or ""


def log_safety_intervention_to_db(db: DBSession, session_id: str, category: str):
    """Log safety intervention to database with truncated session ID."""
    try:
        # Map string category to enum
        category_map = {
            "medical": SafetyCategory.MEDICAL,
            "legal": SafetyCategory.LEGAL,
            "crisis": SafetyCategory.CRISIS,
            "inappropriate": SafetyCategory.INAPPROPRIATE,
        }
        intervention = SafetyIntervention(
            session_id_prefix=session_id[:8],
            category=category_map.get(category, SafetyCategory.INAPPROPRIATE)
        )
        db.add(intervention)
        db.commit()
    except Exception as e:
        print(f"Failed to log safety intervention: {e}")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/health/db")
def health_db(db: DBSession = Depends(get_db)):
    """Check database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return {"ok": True, "database": "connected"}
    except Exception as e:
        return {"ok": False, "database": str(e)}

@app.options("/chat")
async def chat_options():
    return {"message": "OK"}

@app.post("/chat", response_model=ChatOut)
async def chat(payload: ChatIn, db: DBSession = Depends(get_db)):
    # Check if OpenAI API key is configured
    if not openai_client:
        return ChatOut(
            session_id=payload.session_id,
            reply="OpenAI API key not configured. Please add OPENAI_API_KEY to your environment."
        )

    # Load or create session from database
    session = get_or_create_session(db, payload.session_id)

    # Safety check - intercept high-risk content before LLM call
    safety_result = safety_router.check_safety(payload.message)

    if not safety_result.is_safe:
        # Log the safety intervention to database
        if safety_result.category:
            log_safety_intervention_to_db(db, payload.session_id, safety_result.category.value)

        # Return safe response template
        return ChatOut(
            session_id=str(session.id),
            reply=safety_result.safe_response,
            has_summary=session.summary is not None
        )

    try:
        # Build system prompt with conversation context
        base_prompt = prompts.get_prompt("system", "base")

        # Add conversation summary context if available
        if session.summary:
            system_prompt = prompts.render_prompt(
                "system", "with_summary",
                base=base_prompt,
                summary=session.summary,
            )
        else:
            system_prompt = base_prompt

        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload.message}
            ],
            max_tokens=300,
            temperature=0.7
        )

        reply = response.choices[0].message.content

        # Update session state
        session.message_count += 1
        session.last_user_message = payload.message
        session.last_assistant_reply = reply

        # Generate summary every SUMMARY_FREQUENCY messages
        if session.message_count % SUMMARY_FREQUENCY == 0:
            new_summary = generate_summary(
                session.summary,
                payload.message,
                reply
            )
            session.summary = new_summary
            # Clear temporary message storage after summary generation
            session.last_user_message = None
            session.last_assistant_reply = None

        db.commit()

        return ChatOut(
            session_id=str(session.id),
            reply=reply,
            has_summary=session.summary is not None
        )

    except Exception as e:
        print(f"OpenAI API error: {e}")
        return ChatOut(
            session_id=str(session.id),
            reply="I'm having trouble connecting right now. Please try again in a moment.",
            has_summary=session.summary is not None
        )


# Session management endpoints

@app.get("/sessions/{session_id}", response_model=SessionOut)
async def get_session(session_id: str, db: DBSession = Depends(get_db)):
    """Get session information including summary."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    session = db.query(Session).filter(Session.id == session_uuid).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionOut(
        session_id=str(session.id),
        message_count=session.message_count,
        summary=session.summary,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat()
    )


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: DBSession = Depends(get_db)):
    """
    Delete a session and all associated data.
    GDPR compliance: allows users to request deletion of their data.
    """
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    session = db.query(Session).filter(Session.id == session_uuid).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()

    return {"message": "Session deleted successfully", "session_id": session_id}
