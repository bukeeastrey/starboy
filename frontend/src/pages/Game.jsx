import { useState } from "react";
import { api } from "../api.js";
import { Avatar, ErrorNote, Loading, PlayerName, useLoad } from "../components.jsx";
import { RsvpButtons, inviteMessage, statLine, whatsappLink } from "../game-parts.jsx";
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

      {game.can_report && !game.my_claim && (
        <Link to={`/game/${id}/report`} className="button gold big">
          How was your game? 🎙️ Tell Star Boy
        </Link>
      )}

      {game.flags.includes("numbers_dont_add_up") && (
        <p className="card unsure">
          Numbers no add up 👀 The confirmed goals are more than the score. Check your reports.
        </p>
      )}

      {game.summary && (
        <section className="card stack highlight">
          <h3>Game summary</h3>
          <p className="verdict">{game.summary.text}</p>
          <a
            className="button gold"
            href={whatsappLink(summaryMessage(game))}
            target="_blank" rel="noreferrer"
          >
            Share to WhatsApp
          </a>
        </section>
      )}

      {game.my_claim && (
        <section className="card stack">
          <div className="row">
            <strong className="row-text">Your report</strong>
            <ClaimStatus claim={game.my_claim} />
          </div>
          <p>{statLine(game.my_claim.stats)}</p>
          {game.my_claim.stats.highlight && (
            <p className="muted">“{game.my_claim.stats.highlight}”</p>
          )}
          {game.my_claim.status === "disputed" && (
            <p className="muted">Your teammates disputed this. Tell Star Boy again with the right numbers.</p>
          )}
          {game.can_report && game.my_claim.status === "confirmed" ? (
            <Link to={`/game/${id}/report?edit=1`}>Ask for an edit (teammates confirm again)</Link>
          ) : game.can_report && (
            <Link to={`/game/${id}/report`}>Something wrong? Tell Star Boy again</Link>
          )}
        </section>
      )}

      {game.claims.length > 0 && (
        <section className="stack">
          <h3>What your teammates said</h3>
          <ul className="list">
            {game.claims.map((claim) => (
              <ClaimCard key={claim.id} claim={claim} onVoted={reload} />
            ))}
          </ul>
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

// The summary as clean text for the crew's WhatsApp group.
function summaryMessage(game) {
  return [
    `⭐ ${game.pitch.name} · ${game.kickoff_label}`,
    "",
    game.summary.text,
    "",
    `${window.location.origin}/game/${game.id}`,
  ].join("\n");
}

// A teammate's report with Confirm ✅ / Dispute ❌ buttons.
function ClaimCard({ claim, onVoted }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function vote(choice) {
    setBusy(true);
    setError("");
    try {
      await api(`/api/claims/${claim.id}/vote`, { method: "POST", body: { vote: choice } });
      await onVoted();
    } catch (err) {
      setError(err.message);
    }
    setBusy(false);
  }

  const player = claim.player;
  return (
    <li className="card stack">
      <div className="row">
        <Avatar user={player} size={36} />
        <span className="row-text">
          <Link to={`/player/${player.id}`} className="player-name">
            {player.nickname || player.name.split(" ")[0]} says:
          </Link>
          <span>{statLine(claim.stats)}</span>
        </span>
        <ClaimStatus claim={claim} />
      </div>
      {claim.stats.highlight && <p className="muted">“{claim.stats.highlight}”</p>}
      {claim.can_vote && (
        <div className="button-row">
          <button
            className={claim.my_vote === "confirm" ? "button" : "button secondary"}
            onClick={() => vote("confirm")} disabled={busy}
          >
            ✅ Confirm
          </button>
          <button
            className={claim.my_vote === "dispute" ? "button danger selected" : "button danger"}
            onClick={() => vote("dispute")} disabled={busy}
          >
            ❌ Dispute
          </button>
        </div>
      )}
      <ErrorNote error={error} />
    </li>
  );
}

function ClaimStatus({ claim }) {
  if (claim.status === "confirmed") return <span className="chip in">Confirmed ✅</span>;
  if (claim.status === "disputed") return <span className="chip out">Disputed</span>;
  return (
    <span className="chip gold">
      {claim.confirms}/{claim.needed} ✅{claim.disputes ? ` · ${claim.disputes} ❌` : ""}
    </span>
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
              <Link to={`/player/${player.id}`}><PlayerName user={player} /></Link>
              <span className="muted">{player.position}</span>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
