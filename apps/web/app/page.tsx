"use client";

import { useState, useEffect } from "react";

type ChatMsg = { role: "user" | "assistant"; text: string };

const SESSION_STORAGE_KEY = "life-story-session-id";

function getOrCreateSessionId(): string {
  // Check localStorage for existing session
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem(SESSION_STORAGE_KEY);
    if (stored) return stored;

    // Generate new session ID and store it
    const newId = crypto.randomUUID();
    localStorage.setItem(SESSION_STORAGE_KEY, newId);
    return newId;
  }
  // Fallback for SSR
  return crypto.randomUUID();
}

export default function Home() {
  const [sessionId, setSessionId] = useState<string>("");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMsg[]>([
    {
      role: "assistant",
      text: "Hi — tell me a bit about a good memory from your life.",
    },
  ]);
  const [loading, setLoading] = useState(false);

  // Initialize session ID from localStorage on mount
  useEffect(() => {
    setSessionId(getOrCreateSessionId());
  }, []);

  const apiBase =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

  async function send() {
    if (!input.trim() || loading || !sessionId) return;

    const userText = input.trim();
    setInput("");
    setMessages((m) => [...m, { role: "user", text: userText }]);
    setLoading(true);

    try {
      const res = await fetch(`${apiBase}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: userText }),
      });

      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();

      setMessages((m) => [...m, { role: "assistant", text: data.reply }]);
    } catch (e: any) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: "Sorry — something went wrong talking to the server.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function startNewSession() {
    const newId = crypto.randomUUID();
    localStorage.setItem(SESSION_STORAGE_KEY, newId);
    setSessionId(newId);
    setMessages([
      {
        role: "assistant",
        text: "Hi — tell me a bit about a good memory from your life.",
      },
    ]);
  }

  return (
    <main
      style={{
        maxWidth: 720,
        margin: "0 auto",
        padding: 24,
        fontFamily: "system-ui",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h1 style={{ fontSize: 22, margin: 0 }}>
          Life Story Chatbot (MVP)
        </h1>
        <button
          onClick={startNewSession}
          style={{
            padding: "6px 12px",
            borderRadius: 6,
            border: "1px solid #ddd",
            background: "#f5f5f5",
            cursor: "pointer",
            fontSize: 14,
          }}
        >
          New Session
        </button>
      </div>

      <div
        style={{
          border: "1px solid #ddd",
          borderRadius: 12,
          padding: 16,
          minHeight: 360,
          marginBottom: 12,
        }}
      >
        {messages.map((m, i) => (
          <div key={i} style={{ marginBottom: 10 }}>
            <strong>{m.role === "user" ? "You" : "Bot"}:</strong> {m.text}
          </div>
        ))}
        {loading && <div>Bot is thinking…</div>}
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => (e.key === "Enter" ? send() : null)}
          placeholder="Write something…"
          style={{
            flex: 1,
            padding: 10,
            borderRadius: 10,
            border: "1px solid #ddd",
          }}
        />
        <button
          onClick={send}
          style={{
            padding: "10px 14px",
            borderRadius: 10,
            border: "1px solid #ddd",
          }}
        >
          Send
        </button>
      </div>
    </main>
  );
}
