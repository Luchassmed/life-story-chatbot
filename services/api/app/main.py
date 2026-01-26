from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from openai import OpenAI
from .safety import SafetyRouter

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

class ChatIn(BaseModel):
    session_id: str
    message: str

class ChatOut(BaseModel):
    session_id: str
    reply: str

@app.get("/health")
def health():
    return {"ok": True}

@app.options("/chat")
async def chat_options():
    return {"message": "OK"}

@app.post("/chat", response_model=ChatOut)
async def chat(payload: ChatIn):
    # Check if OpenAI API key is configured
    if not openai_client:
        return ChatOut(
            session_id=payload.session_id,
            reply="OpenAI API key not configured. Please add OPENAI_API_KEY to your environment."
        )

    # Safety check - intercept high-risk content before LLM call
    safety_result = safety_router.check_safety(payload.message)

    if not safety_result.is_safe:
        # Log the safety intervention (privacy-preserving)
        safety_router.log_safety_intervention(safety_result, payload.session_id)

        # Return safe response template
        return ChatOut(
            session_id=payload.session_id,
            reply=safety_result.safe_response
        )

    try:
        # Basic life story system prompt
        system_prompt = """You are a gentle, supportive companion for older adults. Your role is to:

1. Help them share and explore their life stories through thoughtful questions
2. Engage in everyday small talk and check-ins
3. Listen actively and respond with warmth and interest

Important guidelines:
- Never provide medical, legal, or crisis counseling advice
- If someone mentions health concerns, gently suggest they speak with their doctor
- Keep responses conversational and encouraging
- Ask follow-up questions to help them elaborate on their stories
- Show genuine interest in their experiences and memories

Your goal is to be a caring listener who helps people reflect on and share their life experiences."""

        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Cost-effective model for development
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload.message}
            ],
            max_tokens=300,
            temperature=0.7
        )

        reply = response.choices[0].message.content
        return ChatOut(session_id=payload.session_id, reply=reply)

    except Exception as e:
        # Log the error (in production, use proper logging)
        print(f"OpenAI API error: {e}")
        return ChatOut(
            session_id=payload.session_id,
            reply="I'm having trouble connecting right now. Please try again in a moment."
        )
