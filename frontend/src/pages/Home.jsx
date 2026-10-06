import { api } from "../api.js";
import { ErrorNote, Loading, useLoad } from "../components.jsx";
import { Link } from "../router.jsx";

export default function Home({ user }) {
  const { data, error } = useLoad(() => api("/api/home"), []);
  const firstName = user.nickname || user.name.split(" ")[0];

  return (
    <div className="stack">
      <h2>How far, {firstName}? ⚽</h2>
      <ErrorNote error={error} />
      {!data && !error && <Loading />}

      {data && (
        <section className="stack">
          <h3>Your pitches</h3>
          {data.pitches.length === 0 && (
            <p className="card muted">
              You never register for any pitch yet. Find where your people dey play.
            </p>
          )}
          {data.pitches.map((pitch) => (
            <PitchRow key={pitch.id} pitch={pitch} />
          ))}
          <Link to="/pitches" className="button secondary">Find a pitch</Link>
        </section>
      )}
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
