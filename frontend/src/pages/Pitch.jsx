import { useState } from "react";
import { api } from "../api.js";
import { Avatar, ErrorNote, Loading, PlayerName, useLoad } from "../components.jsx";

const TABS = ["Games", "Players"];

// The columns the Players tab can be sorted by.
const SORTS = [
  ["appearances", "Apps"],
  ["goals", "Goals"],
  ["assists", "Assists"],
];

export default function Pitch({ id, user }) {
  const { data: pitch, error, reload } = useLoad(() => api(`/api/pitches/${id}`), [id]);
  const [tab, setTab] = useState("Games");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");

  async function register() {
    setBusy(true);
    setActionError("");
    try {
      await api(`/api/pitches/${id}/register`, { method: "POST" });
      await reload();
    } catch (err) {
      setActionError(err.message);
    }
    setBusy(false);
  }

  if (error) return <ErrorNote error={error} />;
  if (!pitch) return <Loading />;

  return (
    <div className="stack">
      <header className="pitch-header">
        <h2>{pitch.name}</h2>
        {pitch.area && <p>{pitch.area}</p>}
        {pitch.maps_url && (
          <a href={pitch.maps_url} target="_blank" rel="noreferrer">📍 Open in Maps</a>
        )}
        {pitch.registered ? (
          <span className="chip gold">Registered ✓</span>
        ) : (
          <button className="button gold" onClick={register} disabled={busy}>
            {busy ? "Registering…" : "Register at this pitch"}
          </button>
        )}
      </header>
      <ErrorNote error={actionError} />

      <nav className="tabs">
        {TABS.map((name) => (
          <button
            key={name}
            className={tab === name ? "tab selected" : "tab"}
            onClick={() => setTab(name)}
          >
            {name}
          </button>
        ))}
      </nav>

      {tab === "Games" && <GamesTab pitch={pitch} />}
      {tab === "Players" && <PlayersTab players={pitch.players} me={user} />}
    </div>
  );
}

function GamesTab() {
  return <p className="card muted">No games here yet.</p>;
}

function PlayersTab({ players, me }) {
  const [sortBy, setSortBy] = useState("appearances");

  // Highest number first; equal numbers stay in name order.
  const sorted = [...players].sort((a, b) => b[sortBy] - a[sortBy]);

  if (players.length === 0) {
    return <p className="card muted">Nobody has registered here yet. Be the first! 🥇</p>;
  }

  return (
    <div className="stack">
      <div className="sort-bar">
        <span className="muted">Sort by</span>
        {SORTS.map(([key, label]) => (
          <button
            key={key}
            className={sortBy === key ? "choice small selected" : "choice small"}
            onClick={() => setSortBy(key)}
          >
            {label}
          </button>
        ))}
      </div>

      <ul className="list">
        {sorted.map((player) => (
          <li key={player.id} className="card row">
            <Avatar user={player} />
            <span className="row-text">
              <PlayerName user={player} />
              <span className="muted">
                {player.position}
                {player.id === me.id ? " · You" : ""}
              </span>
            </span>
            <span className="stats">
              {SORTS.map(([key, label]) => (
                <span key={key} className={sortBy === key ? "stat selected" : "stat"}>
                  <strong>{player[key]}</strong>
                  <small>{label}</small>
                </span>
              ))}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
