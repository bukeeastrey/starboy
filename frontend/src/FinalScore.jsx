import { useState } from "react";
import { api } from "./api.js";
import { ErrorNote } from "./components.jsx";

// The final score is entered ONCE, by whoever set the game up. They also say
// who was on their side; everyone else was on the other side. Each player's
// win, loss or draw (and the Most Wins leaderboard) comes from this.
//
// This component is only the entering part. The score itself is shown in the
// scoreboard at the top of the game page.
export default function FinalScore({ game, me, onSaved }) {
  const saved = game.result;
  const [editing, setEditing] = useState(false);
  const [us, setUs] = useState(saved?.us ?? 0);
  const [them, setThem] = useState(saved?.them ?? 0);
  const [team, setTeam] = useState(new Set(saved?.team_a ?? []));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (!game.can_set_result) return null;
  const others = game.players.in.filter((player) => player.id !== me.id);

  function toggle(playerId) {
    const next = new Set(team);
    if (next.has(playerId)) next.delete(playerId);
    else next.add(playerId);
    setTeam(next);
  }

  async function save(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api(`/api/games/${game.id}/result`, {
        method: "POST",
        body: { us: Number(us), them: Number(them), my_team: [...team] },
      });
      setEditing(false);
      await onSaved();
    } catch (err) {
      setError(err.message);
    }
    setBusy(false);
  }

  if (!editing) {
    return saved ? (
      <button className="link-button" onClick={() => setEditing(true)}>Change the score or the sides</button>
    ) : (
      <button className="button gold big" onClick={() => setEditing(true)}>Enter the final score</button>
    );
  }

  return (
    <form className="card form" onSubmit={save}>
      <h3>Final score</h3>
      <div className="score-inputs">
        <label>
          Your side
          <input type="number" inputMode="numeric" min="0" max="50" value={us}
                 onChange={(event) => setUs(event.target.value)} required />
        </label>
        <span>–</span>
        <label>
          Other side
          <input type="number" inputMode="numeric" min="0" max="50" value={them}
                 onChange={(event) => setThem(event.target.value)} required />
        </label>
      </div>

      {others.length > 0 && (
        <fieldset>
          <legend>Who was on your side?</legend>
          <div className="choices">
            {others.map((player) => (
              <button
                key={player.id} type="button"
                className={team.has(player.id) ? "choice selected" : "choice"}
                onClick={() => toggle(player.id)}
              >
                {player.nickname || player.name.split(" ")[0]}
              </button>
            ))}
          </div>
        </fieldset>
      )}

      <ErrorNote error={error} />
      <button className="button" disabled={busy}>{busy ? "Saving…" : "Save score"}</button>
      <button type="button" className="link-button" onClick={() => setEditing(false)}>Cancel</button>
    </form>
  );
}
