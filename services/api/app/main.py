from fastapi import FastAPI
from pydantic import BaseModel
import os

app = FastAPI(title="Life Story Chatbot API")

class ChatIn(BaseModel):
    session_id: str
    message: str

class ChatOut(BaseModel):
    session_id: str
    reply: str

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/chat", response_model=ChatOut)
async def chat(payload: ChatIn):
    # MVP: no real LLM call yet. Just echo + placeholder.
    # Next step: swap this with your provider call + safety routing.
    reply = f"(placeholder) You said: {payload.message}"
    return ChatOut(session_id=payload.session_id, reply=reply)
