import { useState } from "react";
import { api } from "../api.js";
import { Avatar, ErrorNote, Loading, PlayerName, useLoad } from "../components.jsx";
import { navigate } from "../router.jsx";

// Today as "2026-10-09", the format <input type="date"> uses.
function today() {
  const now = new Date();
  const two = (n) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${two(now.getMonth() + 1)}-${two(now.getDate())}`;
}

export default function NewGame({ id, user }) {
  const { data: pitch, error: loadError } = useLoad(() => api(`/api/pitches/${id}`), [id]);
  const [form, setForm] = useState({ date: today(), time: "17:00", duration_min: 90, note: "" });
  const [invited, setInvited] = useState(new Set()); // ids of the ticked players
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (loadError) return <ErrorNote error={loadError} />;
  if (!pitch) return <Loading />;

  // Everyone at the pitch except me (I'm automatically in).
  const others = pitch.players.filter((player) => player.id !== user.id);
  const allSelected = others.length > 0 && invited.size === others.length;

  const set = (field) => (event) => setForm({ ...form, [field]: event.target.value });

  function toggle(playerId) {
    const next = new Set(invited);
    if (next.has(playerId)) next.delete(playerId);
    else next.add(playerId);
    setInvited(next);
  }

  function toggleAll() {
    setInvited(allSelected ? new Set() : new Set(others.map((player) => player.id)));
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const game = await api(`/api/pitches/${id}/games`, {
        method: "POST",
        body: {
          ...form,
          duration_min: Number(form.duration_min),
          invite_user_ids: [...invited],
        },
      });
      // The game page shows a "tell the crew" card once, right after creating.
      sessionStorage.setItem("starboy_new_game", game.id);
      navigate(`/game/${game.id}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <form className="form" onSubmit={submit}>
      <h2>New game at {pitch.name} ⚽</h2>

      <div className="button-row">
        <label>
          Date
          <input type="date" value={form.date} onChange={set("date")} required />
        </label>
        <label>
          Kickoff
          <input type="time" value={form.time} onChange={set("time")} required />
        </label>
      </div>

      <label>
        How long? <span className="muted">(minutes)</span>
        <input
          type="number" min="10" max="300" step="5"
          value={form.duration_min} onChange={set("duration_min")} required
        />
      </label>

      <label>
        Note <span className="muted">(optional)</span>
        <input
          value={form.note} onChange={set("note")} maxLength={200}
          placeholder="Bring white and dark shirts"
        />
      </label>

      <fieldset>
        <legend>Who are you inviting?</legend>
        {others.length === 0 ? (
          <p className="card muted">
            Nobody else has registered here yet. Create the game, then share the
            WhatsApp invite so your people can join.
          </p>
        ) : (
          <div className="card">
            <label className="check">
              <input type="checkbox" checked={allSelected} onChange={toggleAll} />
              <strong>Select all ({others.length})</strong>
            </label>
            {others.map((player) => (
              <label key={player.id} className="check">
                <input
                  type="checkbox"
                  checked={invited.has(player.id)}
                  onChange={() => toggle(player.id)}
                />
                <Avatar user={player} size={32} />
                <PlayerName user={player} />
              </label>
            ))}
          </div>
        )}
      </fieldset>

      <ErrorNote error={error} />
      <button className="button big" disabled={busy}>
        {busy ? "Setting it up…" : `Create game${invited.size ? ` · invite ${invited.size}` : ""}`}
      </button>
    </form>
  );
}
