import { api } from "../api.js";
import { Avatar, ErrorNote, Loading, useLoad } from "../components.jsx";
import { statLine } from "../game-parts.jsx";
import { Link } from "../router.jsx";

// The numbers shown for each pitch: [stat key, label].
const STATS = [
  ["appearances", "Games"],
  ["goals", "Goals"],
  ["assists", "Assists"],
  ["wins", "Wins"],
];

// A player's public profile: no phone number, just football.
export default function Player({ id }) {
  const { data: player, error } = useLoad(() => api(`/api/players/${id}`), [id]);

  if (error) return <ErrorNote error={error} />;
  if (!player) return <Loading />;

  return (
    <div className="stack">
      <header className="pitch-header profile-header">
        <Avatar user={player} size={72} />
        <h2>{player.name}</h2>
        <p>
          {player.nickname && `“${player.nickname}” · `}
          {player.position}
          {player.is_me && " · You"}
        </p>
      </header>

      <h3>Stats by pitch</h3>
      {player.pitch_stats.length === 0 && (
        <p className="card muted">No games reported yet. Time to touch grass! ⚽</p>
      )}
      {player.pitch_stats.map((row) => (
        <section key={row.pitch.id} className="card stack">
          <Link to={`/pitch/${row.pitch.id}`}><strong>{row.pitch.name}</strong></Link>
          <div className="stats wide">
            {STATS.map(([key, label]) => (
              <span key={key} className="stat selected">
                <strong>{row[key]}</strong>
                <small>{label}</small>
              </span>
            ))}
            {row.saves > 0 && (
              <span className="stat selected">
                <strong>{row.saves}</strong>
                <small>Saves</small>
              </span>
            )}
          </div>
        </section>
      ))}

      {player.recent_games.length > 0 && (
        <section className="stack">
          <h3>Recent games</h3>
          <ul className="list">
            {player.recent_games.map((game) => (
              <li key={game.game_id}>
                <Link to={`/game/${game.game_id}`} className="card row">
                  <span className="row-text">
                    <strong>{game.pitch_name} · {game.kickoff_label}</strong>
                    <span className="muted">{statLine(game.stats)}</span>
                  </span>
                  {game.status === "pending" && <span className="chip gold">⏳</span>}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
