import { useRef, useState } from "react";
import { api } from "../api.js";
import { Avatar, ErrorNote, Loading, useLoad } from "../components.jsx";
import { statLine } from "../game-parts.jsx";
import { CountUp } from "../motion.jsx";
import { uploadPhoto } from "../photos.js";
import { Link } from "../router.jsx";

// The six numbers on the front of the card: [stat key, short label].
// Keepers get saves and clean sheets where others get assists and the wall.
const OUTFIELD = [
  ["goals", "GLS"], ["assists", "AST"], ["wins", "WIN"],
  ["motm", "MOTM"], ["appearances", "APP"], ["wall", "DEF"],
];
const KEEPER = [
  ["saves", "SAV"], ["clean_sheets", "CS"], ["wins", "WIN"],
  ["motm", "MOTM"], ["appearances", "APP"], ["goals", "GLS"],
];

const FORM_LETTER = { won: "W", draw: "D", lost: "L" };

// A player's public profile: no phone number, just football.
export default function Player({ id, refreshUser }) {
  const { data: player, error, reload } = useLoad(() => api(`/api/players/${id}`), [id]);
  const [flipped, setFlipped] = useState(false);
  const [busy, setBusy] = useState(false);
  const [photoError, setPhotoError] = useState("");
  const picker = useRef(null);

  // Your own card only: add or change the profile photo.
  async function changePhoto(event) {
    const file = event.target.files[0];
    event.target.value = "";
    if (!file) return;
    setBusy(true);
    setPhotoError("");
    try {
      await uploadPhoto("/api/me/photo", file);
      await Promise.all([reload(), refreshUser()]); // the card, and the avatar in the top bar
    } catch (err) {
      setPhotoError(err.message);
    }
    setBusy(false);
  }

  async function removePhoto() {
    setBusy(true);
    await api("/api/me/photo", { method: "DELETE" }).catch(() => {});
    await Promise.all([reload(), refreshUser()]);
    setBusy(false);
  }

  if (error) return <ErrorNote error={error} />;
  if (!player) return <Loading />;

  return (
    <div className="stack">
      {/* The card has two faces. Tapping it (or the button) turns it over. */}
      <div className={flipped ? "flip flipped" : "flip"}>
        <CardFront player={player} onFlip={() => setFlipped(true)} hidden={flipped} />
        <CardBack player={player} onFlip={() => setFlipped(false)} hidden={!flipped} />
      </div>
      <button className="button secondary" onClick={() => setFlipped(!flipped)}>
        {flipped ? "Front of the card" : "Turn the card over"}
      </button>

      {player.is_me && (
        <p className="center">
          <button className="link-button" onClick={() => picker.current.click()} disabled={busy}>
            {busy ? "Sending…" : player.photo ? "Change your photo" : "Add your photo to the card"}
          </button>
          {player.photo && !busy && (
            <button className="link-button" onClick={removePhoto}>Remove it</button>
          )}
          <input ref={picker} type="file" accept="image/*" hidden onChange={changePhoto} />
        </p>
      )}
      <ErrorNote error={photoError} />

      <h3>By pitch</h3>
      {player.pitch_stats.length === 0 && (
        <p className="card muted">No games reported yet. Time to touch grass.</p>
      )}
      {player.pitch_stats.map((row) => (
        <section key={row.pitch.id} className="card stack">
          <Link to={`/pitch/${row.pitch.id}`} className="player-name">{row.pitch.name}</Link>
          <div className="stats wide">
            {[["appearances", "Games"], ["goals", "Goals"], ["assists", "Assists"], ["wins", "Wins"]].map(
              ([key, label]) => (
                <span key={key} className="stat selected">
                  <strong>{row[key]}</strong>
                  <small>{label}</small>
                </span>
              )
            )}
          </div>
          <Link to={`/settle?pitch=${row.pitch.id}&a=${player.id}`} className="button secondary">
            Settle it with…
          </Link>
        </section>
      ))}
    </div>
  );
}

// The front: position and games in the corner, the photo (or initials), the
// name, six numbers, and the latest "You played like…" as a badge.
function CardFront({ player, onFlip, hidden }) {
  const totals = player.totals;
  const numbers = player.position === "GK" ? KEEPER : OUTFIELD;
  // "Anywhere" is too long for the corner of a card.
  const position = player.position === "Anywhere" ? "ANY" : player.position;

  return (
    <article className="player-card card-front" onClick={onFlip} aria-hidden={hidden}>
      <div className="player-card-face">
        <div className="card-top">
          <div className="card-corner">
            <strong>{position}</strong>
            <span>{totals.appearances} {totals.appearances === 1 ? "game" : "games"}</span>
          </div>
          {player.is_me && <span className="chip gold">You</span>}
        </div>

        <div className="card-avatar">
          <Avatar user={player} size={112} />
        </div>
        <h2 className="card-name">{player.name}</h2>
        {player.nickname && <p className="card-nick">“{player.nickname}”</p>}

        <div className="card-stats">
          {numbers.map(([key, label]) => (
            <div key={key}>
              <strong><CountUp value={Math.round(totals[key] ?? 0)} /></strong>
              <span>{label}</span>
            </div>
          ))}
        </div>

        {player.played_like && (
          <div className="card-badge">
            <small>Last played like</small>
            <strong>{player.played_like.name}</strong>
          </div>
        )}
      </div>
    </article>
  );
}

// The back: form guide, streak, best game, last five games, badges collected.
function CardBack({ player, onFlip, hidden }) {
  const lastFive = player.recent_games.slice(0, 5);
  return (
    <article className="player-card card-back" onClick={onFlip} aria-hidden={hidden}>
      <div className="player-card-face">
        <h2 className="card-name small">{player.name}</h2>

        <div className="back-row">
          <div>
            <small>Form</small>
            {/* Newest game on the right, as in a league table. */}
            <div className="form-guide">
              {player.form.length === 0 && <span className="muted">No confirmed games yet</span>}
              {[...player.form].reverse().map((result, index) => (
                <i key={index} className={`form-dot ${result ?? "none"}`} title={result ?? "no result"}>
                  {FORM_LETTER[result] ?? "–"}
                </i>
              ))}
            </div>
          </div>
          <div>
            <small>Win streak</small>
            <strong className="back-number">{player.streak}</strong>
          </div>
        </div>

        {player.best_game && (
          <div className="back-block">
            <small>Best game</small>
            <p><strong>{statLine({ ...player.best_game.stats, result: null })}</strong></p>
            <p className="muted">{player.best_game.label}</p>
          </div>
        )}

        {lastFive.length > 0 && (
          <div className="back-block">
            <small>Last {lastFive.length} {lastFive.length === 1 ? "game" : "games"}</small>
            <ul className="back-games">
              {lastFive.map((game) => (
                <li key={game.game_id}>
                  <i className={`form-dot small ${game.result ?? "none"}`}>{FORM_LETTER[game.result] ?? "–"}</i>
                  {/* Stop the tap here, so opening a game doesn't also flip the card. */}
                  <Link to={`/game/${game.game_id}`}>
                    <span onClick={(event) => event.stopPropagation()}>
                      {statLine({ ...game.stats, result: null, defending: null })}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}

        {player.badges.length > 0 && (
          <div className="back-block">
            <small>Played like</small>
            <div className="badges">
              {player.badges.map((badge) => (
                <span key={badge.name} className="badge-pill">
                  {badge.name}{badge.times > 1 ? ` ×${badge.times}` : ""}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </article>
  );
}
