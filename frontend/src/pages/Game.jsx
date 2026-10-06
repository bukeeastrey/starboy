import { useState } from "react";
import { api } from "../api.js";
import { Avatar, ErrorNote, Loading, PlayerName, useLoad } from "../components.jsx";
import { RsvpButtons, inviteMessage, whatsappLink } from "../game-parts.jsx";
import { Link } from "../router.jsx";

export default function Game({ id }) {
  const { data: game, error, reload } = useLoad(() => api(`/api/games/${id}`), [id]);
  const [actionError, setActionError] = useState("");

  // True only on the first visit right after creating this game.
  const [justCreated] = useState(() => {
    const created = sessionStorage.getItem("starboy_new_game") === id;
    sessionStorage.removeItem("starboy_new_game");
    return created;
  });

  async function cancel() {
    if (!window.confirm("Cancel this game for everyone?")) return;
    try {
      await api(`/api/games/${id}/cancel`, { method: "POST" });
      await reload();
    } catch (err) {
      setActionError(err.message);
    }
  }

  if (error) return <ErrorNote error={error} />;
  if (!game) return <Loading />;

  const cancelled = game.status === "cancelled";
  const finished = game.phase === "finished";
  const inviteLink = whatsappLink(inviteMessage(game));

  return (
    <div className="stack">
      <header className="pitch-header">
        <Link to={`/pitch/${game.pitch.id}`}>🏟️ {game.pitch.name}</Link>
        <h2>{game.kickoff_label}</h2>
        <p>
          {game.duration_min} minutes
          {game.created_by ? ` · set up by ${game.created_by.name}` : ""}
        </p>
        {game.note && <p>📝 {game.note}</p>}
      </header>

      {cancelled && <p className="error">This game was cancelled.</p>}

      {justCreated && (
        <div className="card stack highlight">
          <strong>Game set! 🎉 Now tell the crew.</strong>
          <a className="button gold" href={inviteLink} target="_blank" rel="noreferrer">
            Send invite on WhatsApp
          </a>
        </div>
      )}

      {!cancelled && !finished && (
        <section className="card stack">
          <strong>{game.phase === "live" ? "Game dey on now!" : "You dey come?"}</strong>
          <RsvpButtons game={game} onDone={reload} />
          {game.my_status === "in" && (
            <a className="button secondary" href={`/api/games/${id}/calendar.ics`} download>
              📅 Add to calendar
            </a>
          )}
        </section>
      )}

      {/* Someone who played but wasn't on the list can still add themselves. */}
      {!cancelled && finished && game.my_status !== "in" && (
        <section className="card stack">
          <strong>Were you there?</strong>
          <RsvpButtons game={game} onDone={reload} />
        </section>
      )}

      <PlayerList title={`In (${game.players.in.length})`} players={game.players.in} />
      <PlayerList title={`No answer yet (${game.players.invited.length})`} players={game.players.invited} />
      <PlayerList title={`Can't make it (${game.players.out.length})`} players={game.players.out} />

      {!cancelled && !finished && !justCreated && (
        <a className="button secondary" href={inviteLink} target="_blank" rel="noreferrer">
          Invite more people on WhatsApp
        </a>
      )}

      <ErrorNote error={actionError} />
      {game.is_creator && !cancelled && !finished && (
        <button className="button danger" onClick={cancel}>Cancel this game</button>
      )}
    </div>
  );
}

function PlayerList({ title, players }) {
  if (players.length === 0) return null;
  return (
    <section className="stack">
      <h3>{title}</h3>
      <ul className="list">
        {players.map((player) => (
          <li key={player.id} className="card row">
            <Avatar user={player} />
            <span className="row-text">
              <PlayerName user={player} />
              <span className="muted">{player.position}</span>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
