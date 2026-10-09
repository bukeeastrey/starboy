import { useEffect, useState } from "react";
import { api } from "./api.js";
import { ErrorNote } from "./components.jsx";

// "Connect Telegram 🔔": reminders are the point of Star Boy, and they
// arrive through the Telegram bot. Shown on Home until the player connects.
export default function TelegramCard({ user, refreshUser }) {
  const [waiting, setWaiting] = useState(false); // true after they opened Telegram
  const [error, setError] = useState("");

  // While they are over in Telegram tapping "Start", keep checking if it worked.
  useEffect(() => {
    if (!waiting) return;
    const timer = setInterval(refreshUser, 3000);
    return () => clearInterval(timer);
  }, [waiting, refreshUser]);

  if (!user.telegram_available || user.telegram_linked) return null;

  async function connect() {
    setError("");
    // Open the tab right away (inside the tap), or phones block it as a pop-up.
    const tab = window.open("", "_blank");
    try {
      const { url } = await api("/api/telegram/link", { method: "POST" });
      if (tab) tab.location = url;
      else window.location.href = url;
      setWaiting(true);
    } catch (err) {
      tab?.close();
      setError(err.message);
    }
  }

  return (
    <section className="card stack highlight">
      <strong>Make Star Boy remind you about games</strong>
      <p className="muted">
        Invites, reminders before kickoff, and “How was your game?” all come
        on Telegram. You can answer with one tap or a voice note.
      </p>
      <button className="button gold" onClick={connect}>Connect Telegram</button>
      {waiting && (
        <p className="muted">
          Telegram opened: tap <strong>Start</strong> there. This card disappears once you're connected.
        </p>
      )}
      <ErrorNote error={error} />
    </section>
  );
}
