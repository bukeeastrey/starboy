import { api } from "../api.js";
import { ErrorNote, Loading, useLoad } from "../components.jsx";
import { GameRow, RsvpButtons, StatusChip } from "../game-parts.jsx";
import { Link } from "../router.jsx";
import TelegramCard from "../TelegramCard.jsx";

export default function Home({ user, refreshUser }) {
  const { data, error, reload } = useLoad(() => api("/api/home"), []);
  const firstName = user.nickname || user.name.split(" ")[0];

  if (error) return <ErrorNote error={error} />;
  if (!data) return <Loading />;

  // The soonest game gets the big card; the rest are a short list.
  const [nextGame, ...laterGames] = data.next_games;

  return (
    <div className="stack">
      <h2>How far, {firstName}? ⚽</h2>
      <TelegramCard user={user} refreshUser={refreshUser} />

      {data.needs_report.map((game) => (
        <section key={game.id} className="card stack highlight">
          <h3>How was your game? 🎙️</h3>
          <p>
            <strong>{game.pitch.name}</strong>
            <br />
            <span className="muted">{game.kickoff_label}</span>
          </p>
          <Link to={`/game/${game.id}/report`} className="button gold">Tell Star Boy</Link>
        </section>
      ))}

      {nextGame && (
        <section className="card stack highlight">
          <h3>Your next game</h3>
          <Link to={`/game/${nextGame.id}`} className="next-game">
            <strong>{nextGame.kickoff_label}</strong>
            <span>{nextGame.pitch.name} · {nextGame.in_count} in</span>
          </Link>
          {nextGame.note && <p className="muted">📝 {nextGame.note}</p>}
          {nextGame.my_status === "invited" ? (
            <RsvpButtons game={nextGame} onDone={reload} />
          ) : (
            <StatusChip status={nextGame.my_status} />
          )}
        </section>
      )}

      {laterGames.length > 0 && (
        <section className="stack">
          <h3>Coming up</h3>
          {laterGames.map((game) => <GameRow key={game.id} game={game} showPitch />)}
        </section>
      )}

      <section className="stack">
        <h3>Your pitches</h3>
        {data.pitches.length === 0 && (
          <p className="card muted">
            You never register for any pitch yet. Find where your people dey play.
          </p>
        )}
        {data.pitches.map((pitch) => <PitchRow key={pitch.id} pitch={pitch} />)}
        <Link to="/pitches" className="button secondary">Find a pitch</Link>
      </section>
    </div>
  );
}

// One pitch in a list. Also used on the "Find a pitch" screen.
export function PitchRow({ pitch }) {
  return (
    <Link to={`/pitch/${pitch.id}`} className="card row">
      <span className="row-icon">🏟️</span>
      <span className="row-text">
        <strong>{pitch.name}</strong>
        <span className="muted">
          {pitch.area ? `${pitch.area} · ` : ""}
          {pitch.player_count} {pitch.player_count === 1 ? "player" : "players"}
        </span>
      </span>
      {pitch.registered && <span className="chip">Registered ✓</span>}
    </Link>
  );
}
