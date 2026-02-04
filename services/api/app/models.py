"""
SQLAlchemy ORM models for Life Story Chatbot.

Privacy-first design: stores summaries, not raw transcripts.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import enum

from .database import Base


class SafetyCategory(enum.Enum):
    """Categories for safety interventions."""
    MEDICAL = "medical"
    LEGAL = "legal"
    CRISIS = "crisis"
    INAPPROPRIATE = "inappropriate"


class Session(Base):
    """
    Represents a conversation session.

    Privacy-first: stores only summaries, not raw conversation transcripts.
    The last_user_message and last_assistant_reply are temporary fields
    used only for generating the next summary, then can be cleared.
    """
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Privacy-first summary storage
    summary = Column(Text, nullable=True)  # Latest conversation summary
    message_count = Column(Integer, default=0, nullable=False)

    # Temporary storage for summary generation (cleared after summary is generated)
    last_user_message = Column(Text, nullable=True)
    last_assistant_reply = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Session {self.id} - {self.message_count} messages>"


class SafetyIntervention(Base):
    """
    Logs safety interventions in a privacy-preserving way.

    Only stores truncated session ID prefix (first 8 chars) to enable
    aggregate analytics without full session tracking.
    """
    __tablename__ = "safety_interventions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id_prefix = Column(String(8), nullable=False)  # Truncated for privacy
    category = Column(SQLEnum(SafetyCategory), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<SafetyIntervention {self.category.value} at {self.created_at}>"
