import { useState } from "react";
import { api } from "../api.js";
import { Avatar, ErrorNote, Loading, PlayerName, useLoad } from "../components.jsx";
import { MedalIcon } from "../Crest.jsx";
import FinalScore from "../FinalScore.jsx";
import Gallery from "../Gallery.jsx";
import { PlayedLike, RsvpButtons, inviteMessage, statLine, whatsappLink } from "../game-parts.jsx";
import { Burst, Countdown, CountUp, useFirstTime } from "../motion.jsx";
import { Link } from "../router.jsx";

const shortName = (player) => player.nickname || player.name.split(" ")[0];

// A game's page. Before kickoff it is an invitation: who's in, are you coming.
// After the final whistle it is a match report: the scoreboard, the two
// sides, the man of the match, everyone's line, the photos and the summary.
export default function Game({ id, user }) {
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
  const started = game.phase !== "upcoming";
  const inviteLink = whatsappLink(inviteMessage(game));

  // Every report by player id (mine included), for the lines under each name.
  const reports = {};
  for (const claim of [game.my_claim, ...game.claims]) {
    if (claim?.player && claim.status !== "disputed") reports[claim.player.id] = claim;
  }
  // Reports still waiting for MY vote get their own section with buttons.
  const toConfirm = game.claims.filter((claim) => claim.can_vote);

  return (
    <div className="stack">
      <Scoreboard game={game} />

      {cancelled && <p className="error">This game was cancelled.</p>}

      {justCreated && (
        <div className="card stack highlight">
          <strong>Game set! Now tell the crew.</strong>
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
              Add to calendar
            </a>
          )}
        </section>
      )}

      {game.can_report && !game.my_claim && (
        <Link to={`/game/${id}/report`} className="button gold big">
          How was your game? Tell Star Boy
        </Link>
      )}

      {!cancelled && started && <FinalScore game={game} me={user} onSaved={reload} />}

      {game.motm && <Spotlight game={game} report={reports[game.motm.id]} me={user} />}

      {game.flags.includes("numbers_dont_add_up") && (
        <p className="card unsure">
          Numbers no add up. The confirmed goals are more than the score. Check your reports.
        </p>
      )}

      {game.my_claim && <MyReport game={game} />}

      {toConfirm.length > 0 && (
        <section className="stack">
          <h3>Na true? Confirm your teammates</h3>
          <ul className="list">
            {toConfirm.map((claim) => (
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

      <Sides game={game} reports={reports} started={started} />

      {!cancelled && started && <Gallery game={game} onChange={reload} />}

      {game.summary && (
        <section className="card stack highlight">
          <h3>Match report</h3>
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

// The top of the page: a stadium scoreboard. Before the game it counts
// down to kickoff; after it, it shows the final score between the two sides.
function Scoreboard({ game }) {
  const result = game.result;
  const upcoming = game.phase === "upcoming" && game.status !== "cancelled";
  const captain = game.created_by ? shortName(game.created_by) : "Home";
  const mine = { won: "You won", lost: "You lost", draw: "A draw" }[result?.my_result];

  return (
    <header className="matchboard">
      <Link to={`/pitch/${game.pitch.id}`} className="matchboard-pitch">{game.pitch.name}</Link>
      <p className="matchboard-when">{game.kickoff_label} · {game.duration_min} min</p>

      {result ? (
        <>
          <div className="matchboard-score">
            <span className="side-name">{captain}'s side</span>
            <strong><CountUp value={result.us} /><i>:</i><CountUp value={result.them} /></strong>
            <span className="side-name">Other side</span>
          </div>
          <p className="matchboard-status">
            Full time{game.my_status === "in" && mine ? ` · ${mine}` : ""}
          </p>
        </>
      ) : upcoming ? (
        <>
          <Countdown to={game.kickoff_at} />
          <p className="matchboard-status">to kickoff · {game.in_count} in</p>
        </>
      ) : (
        <p className="matchboard-status big">
          {game.status === "cancelled" ? "Cancelled" : game.phase === "live" ? "Playing now" : "Full time · score not in yet"}
        </p>
      )}

      {game.note && <p className="matchboard-note">{game.note}</p>}
    </header>
  );
}

// The man of the match, given room to breathe. The first time YOU see your
// own award, it comes with a small gold burst.
function Spotlight({ game, report, me }) {
  const player = game.motm;
  const celebrate = useFirstTime(player.id === me.id ? `starboy_motm_${game.id}` : null);
  return (
    <section className="spotlight">
      {celebrate && <Burst />}
      <span className="spotlight-label"><MedalIcon size={20} /> Man of the match</span>
      <Link to={`/player/${player.id}`} className="spotlight-player">
        <Avatar user={player} size={72} />
        <strong>{player.name}</strong>
      </Link>
      {report && <p>{statLine({ ...report.stats, result: null })}</p>}
      {report?.played_like?.name && (
        <p className="spotlight-like">Played like {report.played_like.name}</p>
      )}
    </section>
  );
}

// Your own report: its status, and the "You played like…" line, which also
// gets a burst the first time you see a new badge.
function MyReport({ game }) {
  const claim = game.my_claim;
  const badge = claim.played_like?.name;
  const celebrate = useFirstTime(badge ? `starboy_badge_${game.id}_${badge}` : null);
  return (
    <section className="card stack my-report">
      {celebrate && <Burst />}
      <div className="row">
        <strong className="row-text">Your report</strong>
        <ClaimStatus claim={claim} />
      </div>
      <p>{statLine({ ...claim.stats, result: null })}</p>
      <PlayedLike playedLike={claim.played_like} you />
      {claim.stats.highlight && <p className="muted">“{claim.stats.highlight}”</p>}
      {claim.status === "disputed" && (
        <p className="muted">Your teammates disputed this. Tell Star Boy again with the right numbers.</p>
      )}
      {game.can_report && claim.status === "confirmed" ? (
        <Link to={`/game/${game.id}/report?edit=1`}>Ask for an edit (teammates confirm again)</Link>
      ) : game.can_report && (
        <Link to={`/game/${game.id}/report`}>Something wrong? Tell Star Boy again</Link>
      )}
    </section>
  );
}

// Who played. Once the creator has entered the score and the sides, the
// players are shown as two teams; before that, as one squad.
function Sides({ game, reports, started }) {
  const players = game.players.in;
  if (players.length === 0) return null;

  if (!game.result) {
    return (
      <section className="stack">
        <h3>{started ? `Squad (${players.length})` : `In (${players.length})`}</h3>
        <ul className="list">
          {players.map((player) => (
            <SquadRow key={player.id} player={player} report={reports[player.id]} started={started} />
          ))}
        </ul>
      </section>
    );
  }

  const onA = new Set(game.result.team_a);
  const captain = game.created_by ? shortName(game.created_by) : "Home";
  const teams = [
    [`${captain}'s side`, game.result.us, players.filter((p) => onA.has(p.id))],
    ["Other side", game.result.them, players.filter((p) => !onA.has(p.id))],
  ];
  return (
    <section className="stack">
      {teams.map(([name, goals, team]) => team.length > 0 && (
        <div key={name} className="side">
          <h3>{name} <b>{goals}</b></h3>
          <ul className="list">
            {team.map((player) => (
              <SquadRow key={player.id} player={player} report={reports[player.id]} started />
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}

// One player's line in the match report: "2 goals · 1 assist · played like Okocha".
function SquadRow({ player, report, started }) {
  let line = player.position;
  if (report) {
    line = statLine({ ...report.stats, result: null });
    if (report.played_like?.name) line += ` · played like ${report.played_like.name}`;
  } else if (started) {
    line = "No report yet";
  }
  return (
    <li className="card row">
      <Avatar user={player} />
      <span className="row-text">
        <Link to={`/player/${player.id}`}><PlayerName user={player} /></Link>
        <span className="muted">{line}</span>
      </span>
      {report?.status === "pending" && <span className="chip">Pending</span>}
    </li>
  );
}

// The summary as clean text for the crew's WhatsApp group.
function summaryMessage(game) {
  // Who played like which legend, and the man of the match.
  const extras = [game.my_claim, ...game.claims]
    .filter((claim) => claim?.played_like?.name && claim.player)
    .map((claim) => `${shortName(claim.player)} played like ${claim.played_like.name}`);
  if (game.motm) extras.unshift(`Man of the match: ${game.motm.name}`);
  return [
    `⭐ ${game.pitch.name} · ${game.kickoff_label}`,
    "",
    game.summary.text,
    ...(extras.length ? ["", ...extras] : []),
    "",
    `${window.location.origin}/game/${game.id}`,
  ].join("\n");
}

// A teammate's report waiting for your vote, with Confirm / Dispute buttons.
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
          <Link to={`/player/${player.id}`} className="player-name">{shortName(player)} says:</Link>
          <span>{statLine({ ...claim.stats, result: null })}</span>
        </span>
        <ClaimStatus claim={claim} />
      </div>
      {claim.stats.highlight && <p className="muted">“{claim.stats.highlight}”</p>}
      <div className="button-row">
        <button
          className={claim.my_vote === "confirm" ? "button" : "button secondary"}
          onClick={() => vote("confirm")} disabled={busy}
        >
          Confirm
        </button>
        <button
          className={claim.my_vote === "dispute" ? "button danger selected" : "button danger"}
          onClick={() => vote("dispute")} disabled={busy}
        >
          Dispute
        </button>
      </div>
      <ErrorNote error={error} />
    </li>
  );
}

function ClaimStatus({ claim }) {
  if (claim.status === "confirmed") return <span className="chip in">Confirmed</span>;
  if (claim.status === "disputed") return <span className="chip out">Disputed</span>;
  return (
    <span className="chip gold">
      {claim.confirms} of {claim.needed} confirms{claim.disputes ? ` · ${claim.disputes} against` : ""}
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
