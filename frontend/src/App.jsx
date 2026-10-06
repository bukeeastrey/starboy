import { useEffect, useState } from "react";
import { api } from "./api.js";

// What to show for each answer from /api/health.
const DB_MESSAGES = {
  ok: "Database connected ✅",
  not_configured: "Database not set up yet (add MONGODB_URI to .env)",
  error: "Can't reach the database ❌",
};

export default function App() {
  // null = still checking, otherwise the JSON from /api/health (or an error).
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api("/api/health")
      .then(setHealth)
      .catch(() => setHealth({ status: "down" }));
  }, []);

  let statusText = "Checking the server…";
  if (health) {
    statusText =
      health.status === "ok"
        ? `Server is up ✅ · ${DB_MESSAGES[health.db] ?? health.db}`
        : "Can't reach the server ❌";
  }

  return (
    <div className="app">
      <main className="welcome">
        <div className="logo">⭐</div>
        <h1>Star Boy</h1>
        <p className="tagline">Comot for room. Come play ball. ⚽</p>
        <div className="card">
          <p className="status">{statusText}</p>
        </div>
      </main>
      <footer className="badge">
        AI: Gemma + Whisper, open models running on Star Boy's own server
      </footer>
    </div>
  );
}
