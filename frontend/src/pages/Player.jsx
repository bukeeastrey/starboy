import { api } from "../api.js";
import { Avatar, ErrorNote, Loading, useLoad } from "../components.jsx";
import { statLine } from "../game-parts.jsx";
import { Link } from "../router.jsx";

// The six numbers on the card: [stat key, short label].
// Keepers get saves and clean sheets where others get assists and the wall.
const OUTFIELD = [
  ["goals", "GLS"], ["assists", "AST"], ["wins", "WIN"],
  ["motm", "MOTM"], ["appearances", "APP"], ["wall", "DEF"],
];
const KEEPER = [
  ["saves", "SAV"], ["clean_sheets", "CS"], ["wins", "WIN"],
  ["motm", "MOTM"], ["appearances", "APP"], ["goals", "GLS"],
];

// A player's public profile: no phone number, just football.
export default function Player({ id }) {
  const { data: player, error } = useLoad(() => api(`/api/players/${id}`), [id]);

  if (error) return <ErrorNote error={error} />;
  if (!player) return <Loading />;

  return (
    <div className="stack">
      <PlayerCard player={player} />

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

      {player.recent_games.length > 0 && (
        <section className="stack">
          <h3>Recent games</h3>
          <ul className="list">
            {player.recent_games.map((game) => (
              <li key={game.game_id}>
                <Link to={`/game/${game.game_id}`} className="card row">
                  <span className="row-text">
                    <strong>{game.pitch_name} · {game.kickoff_label}</strong>
                    <span className="muted">{statLine({ ...game.stats, result: null })}</span>
                  </span>
                  {game.status === "pending" && <span className="chip gold">Pending</span>}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

// The collector's card: position and games in the corner, the avatar, the
// name, six numbers, and the latest "You played like…" as a badge.
function PlayerCard({ player }) {
  const totals = player.totals;
  const numbers = player.position === "GK" ? KEEPER : OUTFIELD;
  // "Anywhere" is too long for the corner of a card.
  const position = player.position === "Anywhere" ? "ANY" : player.position;

  return (
    <article className="player-card">
      <div className="player-card-face">
        <div className="card-top">
          <div className="card-corner">
            <strong>{position}</strong>
            <span>{totals.appearances} {totals.appearances === 1 ? "game" : "games"}</span>
          </div>
          {player.is_me && <span className="chip gold">You</span>}
        </div>

        <div className="card-avatar">
          <Avatar user={player} size={104} />
        </div>
        <h2 className="card-name">{player.name}</h2>
        {player.nickname && <p className="card-nick">“{player.nickname}”</p>}

        <div className="card-stats">
          {numbers.map(([key, label]) => (
            <div key={key}>
              <strong>{Math.round(totals[key] ?? 0)}</strong>
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
