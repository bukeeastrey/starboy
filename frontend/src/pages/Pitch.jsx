import { useRef, useState } from "react";
import { api } from "../api.js";
import { Avatar, ErrorNote, Loading, PlayerName, useLoad } from "../components.jsx";
import { GameRow, whatsappLink } from "../game-parts.jsx";
import Moments from "../Moments.jsx";
import { stockCover, uploadPhoto } from "../photos.js";
import { Link } from "../router.jsx";

const TABS = ["Games", "Players", "Leaderboards"];

// The four boards: key from the API, title, the stat shown, its unit.
const BOARDS = [
  ["golden_boot", "Golden Boot", "goals", "goals"],
  ["playmaker", "Playmaker", "assists", "assists"],
  ["most_motm", "Most MOTM", "motm", "awards"],
  ["the_wall", "The Wall", "wall", "blocks + tackles"],
  ["most_wins", "Most Wins", "wins", "wins"],
  ["most_consistent", "Most Consistent", "appearances", "games"],
];

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
  const coverPicker = useRef(null);

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

  // Any registered player can set or replace the pitch's cover photo.
  async function changeCover(event) {
    const file = event.target.files[0];
    event.target.value = "";
    if (!file) return;
    setBusy(true);
    setActionError("");
    try {
      await uploadPhoto(`/api/pitches/${id}/cover`, file);
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
      <header className="pitch-header has-cover">
        {/* The crew's own photo of the pitch, or a stock one until they add it. */}
        <img className="cover-photo" src={pitch.cover?.full ?? stockCover(pitch.id)} alt="" />
        <h2>{pitch.name}</h2>
        {pitch.area && <p>{pitch.area}</p>}
        {pitch.maps_url && (
          <a href={pitch.maps_url} target="_blank" rel="noreferrer"> Open in Maps</a>
        )}
        {pitch.registered ? (
          <span className="cover-actions">
            <span className="chip gold">Registered</span>
            <button className="link-button" onClick={() => coverPicker.current.click()} disabled={busy}>
              {busy ? "Sending…" : pitch.cover ? "Change photo" : "Add a photo of this pitch"}
            </button>
            <input ref={coverPicker} type="file" accept="image/*" hidden onChange={changeCover} />
          </span>
        ) : (
          <button className="button gold" onClick={register} disabled={busy}>
            {busy ? "Registering…" : "Register at this pitch"}
          </button>
        )}
      </header>
      <ErrorNote error={actionError} />

      <Moments moments={pitch.moments} />

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
      {tab === "Players" && <PlayersTab players={pitch.players} me={user} pitchId={pitch.id} />}
      {tab === "Leaderboards" && <LeaderboardsTab pitch={pitch} />}
    </div>
  );
}

function GamesTab({ pitch }) {
  const { upcoming, recent } = pitch.games;
  return (
    <div className="stack">
      <Link to={`/pitch/${pitch.id}/new-game`} className="button">+ New game</Link>

      {upcoming.length === 0 && (
        <p className="card muted">No game set yet. Na you go start am?</p>
      )}
      {upcoming.map((game) => <GameRow key={game.id} game={game} />)}

      {recent.length > 0 && <h3>Recent games</h3>}
      {recent.map((game) => <GameRow key={game.id} game={game} />)}
    </div>
  );
}

function PlayersTab({ players, me, pitchId }) {
  const [sortBy, setSortBy] = useState("appearances");

  // Highest number first; equal numbers stay in name order.
  const sorted = [...players].sort((a, b) => b[sortBy] - a[sortBy]);

  if (players.length === 0) {
    return <p className="card muted">Nobody has registered here yet. Be the first!</p>;
  }

  return (
    <div className="stack">
      {players.length > 1 && (
        <Link to={`/settle?pitch=${pitchId}`} className="button secondary">
          Settle it: who's been better?
        </Link>
      )}
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
              <Link to={`/player/${player.id}`}><PlayerName user={player} /></Link>
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

// The pitch's leaderboards (confirmed stats only), plus a WhatsApp share.
function LeaderboardsTab({ pitch }) {
  const boards = pitch.leaderboards;
  const empty = BOARDS.every(([key]) => boards[key].length === 0);
  if (empty) {
    return (
      <p className="card muted">
        No confirmed stats yet. Play a game, tell Star Boy how it went, and
        confirm each other's reports. The leaderboards fill up from there.
      </p>
    );
  }

  return (
    <div className="stack">
      {BOARDS.map(([key, title, stat, unit]) => (
        <section key={key} className="scoreboard">
          <div className="scoreboard-title">
            <strong>{title}</strong>
            <span>{unit}</span>
          </div>
          {boards[key].length === 0 && <p className="muted" style={{ padding: "12px 14px" }}>Nobody yet.</p>}
          <ol className="board">
            {boards[key].map((player, index) => (
              <li key={player.id} className="row">
                <span className={index === 0 ? "rank first" : "rank"}>{index + 1}</span>
                <Avatar user={player} size={32} />
                <Link to={`/player/${player.id}`} className="row-text">
                  <PlayerName user={player} />
                </Link>
                <strong className="board-number">{player[stat]}</strong>
              </li>
            ))}
          </ol>
        </section>
      ))}
      <a
        className="button gold"
        href={whatsappLink(leaderboardMessage(pitch))}
        target="_blank" rel="noreferrer"
      >
        Share leaderboard to WhatsApp
      </a>
    </div>
  );
}

// Clean text for the crew's WhatsApp group: top 3 of each board.
function leaderboardMessage(pitch) {
  const lines = [`⭐ ${pitch.name} leaderboard`];
  for (const [key, title, stat] of BOARDS) {
    const top = pitch.leaderboards[key].slice(0, 3);
    if (top.length === 0) continue;
    lines.push("", title);
    top.forEach((player, i) => {
      lines.push(`${i + 1}. ${player.nickname || player.name} (${player[stat]})`);
    });
  }
  lines.push("", "Confirmed stats only.", `${window.location.origin}/pitch/${pitch.id}`);
  return lines.join("\n");
}
