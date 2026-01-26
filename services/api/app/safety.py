"""
Safety Router for Life Story Chatbot

This module implements safety checks to detect and handle high-risk topics
that should not be processed by the LLM, including:
- Medical advice requests
- Legal advice requests
- Crisis/self-harm content
- Inappropriate requests

Following the principle that the system is NOT a medical device and must
redirect users to appropriate professional resources.
"""

import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass


class SafetyCategory(Enum):
    MEDICAL = "medical"
    LEGAL = "legal"
    CRISIS = "crisis"
    SELF_HARM = "self_harm"
    INAPPROPRIATE = "inappropriate"


@dataclass
class SafetyResult:
    is_safe: bool
    category: Optional[SafetyCategory] = None
    confidence: float = 0.0
    matched_patterns: List[str] = None
    safe_response: Optional[str] = None


class SafetyRouter:
    """
    Rule-based safety router for detecting high-risk content.

    Uses keyword patterns and simple heuristics to identify content that
    should not be processed by the LLM and instead return safe template responses.
    """

    def __init__(self):
        self.medical_patterns = [
            r'\b(?:diagnose|diagnosis|treatment|medicine|medication|prescription|pills|disease|illness|symptoms|pain|hurt|doctor|hospital|emergency)\b',
            r'\b(?:what.{0,10}wrong.{0,10}me|am.{0,5}i.{0,5}sick|feel.{0,10}unwell|health.{0,10}problem)\b',
            r'\b(?:should.{0,5}i.{0,5}take|what.{0,10}medicine|medical.{0,10}advice)\b'
        ]

        self.legal_patterns = [
            r'\b(?:legal|lawyer|attorney|court|sue|lawsuit|contract|will|testament|legal.{0,10}advice)\b',
            r'\b(?:what.{0,10}my.{0,10}rights|can.{0,5}i.{0,5}sue|legal.{0,10}help)\b'
        ]

        self.crisis_patterns = [
            r'\b(?:kill.{0,10}myself|end.{0,10}my.{0,10}life|want.{0,10}to.{0,10}die|suicide|suicidal)\b',
            r'\b(?:hurt.{0,10}myself|harm.{0,10}myself|don.t.{0,10}want.{0,10}to.{0,10}live)\b',
            r'\b(?:emergency|help.{0,5}me|crisis|desperate)\b'
        ]

        self.inappropriate_patterns = [
            r'\b(?:ignore.{0,10}instructions|pretend.{0,10}you.{0,10}are|act.{0,10}like|roleplay)\b'
        ]

        # Compile patterns for efficiency
        self.compiled_patterns = {
            SafetyCategory.MEDICAL: [re.compile(p, re.IGNORECASE) for p in self.medical_patterns],
            SafetyCategory.LEGAL: [re.compile(p, re.IGNORECASE) for p in self.legal_patterns],
            SafetyCategory.CRISIS: [re.compile(p, re.IGNORECASE) for p in self.crisis_patterns],
            SafetyCategory.INAPPROPRIATE: [re.compile(p, re.IGNORECASE) for p in self.inappropriate_patterns]
        }

        # Safe response templates
        self.safe_responses = {
            SafetyCategory.MEDICAL: (
                "I understand you may have health concerns. For any medical questions or symptoms, "
                "it's important to speak with a healthcare professional like your doctor or call your "
                "local health services. I'm here to chat about your life stories and everyday experiences instead. "
                "Is there a memory or experience you'd like to share with me?"
            ),
            SafetyCategory.LEGAL: (
                "I can't provide legal advice or guidance on legal matters. For legal questions, "
                "it's best to consult with a qualified lawyer or legal aid service. "
                "Let's focus on sharing some of your life experiences instead - "
                "perhaps a story about your work life or family?"
            ),
            SafetyCategory.CRISIS: (
                "I'm concerned about you and want to make sure you get the right support. "
                "Please reach out to a crisis helpline, your doctor, or emergency services if you need immediate help. "
                "In Denmark, you can call 70 201 201 for mental health support. "
                "You're important and there are people who want to help."
            ),
            SafetyCategory.INAPPROPRIATE: (
                "I'm designed to be a supportive companion for sharing life stories and everyday conversations. "
                "Let's keep our chat focused on your experiences, memories, and daily life. "
                "What's something interesting that happened to you recently?"
            )
        }

    def check_safety(self, message: str) -> SafetyResult:
        """
        Check if a message contains high-risk content.

        Args:
            message: User message to check

        Returns:
            SafetyResult with safety determination and response if unsafe
        """
        message_lower = message.lower().strip()

        # Check each category
        for category, patterns in self.compiled_patterns.items():
            matched_patterns = []
            for pattern in patterns:
                if pattern.search(message_lower):
                    matched_patterns.append(pattern.pattern)

            if matched_patterns:
                return SafetyResult(
                    is_safe=False,
                    category=category,
                    confidence=1.0,  # Simple binary classification for now
                    matched_patterns=matched_patterns,
                    safe_response=self.safe_responses[category]
                )

        # If no patterns matched, it's safe
        return SafetyResult(is_safe=True)

    def log_safety_intervention(self, result: SafetyResult, session_id: str) -> None:
        """
        Log safety intervention in a privacy-preserving way.

        Args:
            result: SafetyResult that triggered intervention
            session_id: Session ID (for aggregated analytics only)
        """
        # TODO: Implement privacy-preserving logging
        # For now, just print (in production, use proper logging)
        if not result.is_safe:
            print(f"Safety intervention: category={result.category.value}, session={session_id[:8]}...")