// Pieces about games that several screens share.

import { useState } from "react";
import { api } from "./api.js";
import { ErrorNote } from "./components.jsx";
import { Link } from "./router.jsx";

// The little label that says what you answered.
export function StatusChip({ status }) {
  if (status === "in") return <span className="chip in">You're in ✅</span>;
  if (status === "out") return <span className="chip out">Can't make it</span>;
  if (status === "invited") return <span className="chip gold">You dey come?</span>;
  return null;
}

// One game in a list. Tapping it opens the game page.
export function GameRow({ game, showPitch = false }) {
  return (
    <Link to={`/game/${game.id}`} className="card row">
      <span className="row-icon">⚽</span>
      <span className="row-text">
        <strong>{game.kickoff_label}</strong>
        <span className="muted">
          {showPitch ? `${game.pitch.name} · ` : ""}
          {game.in_count} in
          {game.phase === "live" ? " · Playing now" : ""}
        </span>
      </span>
      <StatusChip status={game.my_status} />
    </Link>
  );
}

// "I'm in ✅ / Can't make it ❌". Calls onDone after the answer is saved.
export function RsvpButtons({ game, onDone }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function answer(status) {
    setBusy(true);
    setError("");
    try {
      await api(`/api/games/${game.id}/rsvp`, { method: "POST", body: { status } });
      await onDone();
    } catch (err) {
      setError(err.message);
    }
    setBusy(false);
  }

  return (
    <>
      <div className="button-row">
        <button
          className={game.my_status === "in" ? "button" : "button secondary"}
          onClick={() => answer("in")} disabled={busy}
        >
          I'm in ✅
        </button>
        <button
          className={game.my_status === "out" ? "button" : "button secondary"}
          onClick={() => answer("out")} disabled={busy}
        >
          Can't make it ❌
        </button>
      </div>
      <ErrorNote error={error} />
    </>
  );
}

// A link that opens WhatsApp with a message ready to send.
export function whatsappLink(text) {
  return `https://wa.me/?text=${encodeURIComponent(text)}`;
}

// The invite people paste into the crew's WhatsApp group.
export function inviteMessage(game) {
  const lines = [
    `⚽ Football at ${game.pitch.name}`,
    `🗓 ${game.kickoff_label}`,
  ];
  if (game.note) lines.push(`📝 ${game.note}`);
  lines.push("", "You dey come? Tap to answer:", `${window.location.origin}/game/${game.id}`);
  return lines.join("\n");
}
