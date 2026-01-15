"use client";

import { useState } from "react";

type ChatMsg = { role: "user" | "assistant"; text: string };

export default function Home() {
  const [sessionId] = useState(() => crypto.randomUUID());
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMsg[]>([
    {
      role: "assistant",
      text: "Hi — tell me a bit about a good memory from your life.",
    },
  ]);
  const [loading, setLoading] = useState(false);

  const apiBase =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

  async function send() {
    if (!input.trim() || loading) return;

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

  return (
    <main
      style={{
        maxWidth: 720,
        margin: "0 auto",
        padding: 24,
        fontFamily: "system-ui",
      }}
    >
      <h1 style={{ fontSize: 22, marginBottom: 12 }}>
        Life Story Chatbot (MVP)
      </h1>

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
