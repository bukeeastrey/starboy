import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Avatar, ErrorNote, Loading, useLoad } from "../components.jsx";
import { whatsappLink } from "../game-parts.jsx";
import { Link } from "../router.jsx";

const POLL_MS = 2000;

// "Settle it": pick Player A vs Player B, get the numbers and Star Boy's verdict.
// Opened as /settle?pitch=<id> (optionally with &a=<player id>).
export default function Settle({ user }) {
  const [query] = useState(() => new URLSearchParams(window.location.search));
  const pitchId = query.get("pitch");
  const { data: pitch, error: loadError } = useLoad(
    () => (pitchId ? api(`/api/pitches/${pitchId}`) : Promise.reject(new Error("Open Settle it from a pitch."))),
    [pitchId]
  );

  const [a, setA] = useState(query.get("a") || user.id);
  const [b, setB] = useState("");
  const [gameId, setGameId] = useState(""); // "" = this pitch, all time
  const [result, setResult] = useState(null); // the table (comes at once)
  const [verdict, setVerdict] = useState(null); // Gemma's words (come later)
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Ask every 2 seconds until the verdict job is done.
  useEffect(() => {
    if (!result?.job_id || verdict) return;
    let stopped = false;
    let timer;
    async function poll() {
      try {
        const job = await api(`/api/jobs/${result.job_id}`);
        if (stopped) return;
        if (job.status === "done") return setVerdict(job.result.text);
        if (job.status === "error") return setVerdict("Star Boy couldn't write a verdict this time. The numbers above still stand.");
      } catch {
        // A network blip: try again at the next poll.
      }
      timer = setTimeout(poll, POLL_MS);
    }
    poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [result, verdict]);

  if (loadError) return <ErrorNote error={loadError} />;
  if (!pitch) return <Loading />;

  async function settle(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setResult(null);
    setVerdict(null);
    try {
      setResult(await api("/api/settle", {
        method: "POST",
        body: { player_a: a, player_b: b, pitch_id: pitchId, game_id: gameId },
      }));
    } catch (err) {
      setError(err.message);
    }
    setBusy(false);
  }

  const options = pitch.players.map((player) => (
    <option key={player.id} value={player.id}>
      {player.name}{player.nickname ? ` “${player.nickname}”` : ""}
    </option>
  ));

  return (
    <div className="stack">
      <div>
        <h2>Settle it ⚖️</h2>
        <p className="muted">
          <Link to={`/pitch/${pitch.id}`}>{pitch.name}</Link> · confirmed stats only
        </p>
      </div>

      <form className="form card" onSubmit={settle}>
        <label>
          Player A
          <select value={a} onChange={(e) => setA(e.target.value)} required>
            <option value="">Pick a player</option>
            {options}
          </select>
        </label>
        <label>
          Player B
          <select value={b} onChange={(e) => setB(e.target.value)} required>
            <option value="">Pick a player</option>
            {options}
          </select>
        </label>
        <label>
          Based on
          <select value={gameId} onChange={(e) => setGameId(e.target.value)}>
            <option value="">This pitch, all time</option>
            {pitch.games.recent.map((game) => (
              <option key={game.id} value={game.id}>One game: {game.kickoff_label}</option>
            ))}
          </select>
        </label>
        <ErrorNote error={error} />
        <button className="button gold big" disabled={busy || !a || !b || a === b}>
          {busy ? "Checking the numbers…" : "Settle it ⚖️"}
        </button>
      </form>

      {result && !result.enough && <p className="card unsure">{result.message}</p>}
      {result?.enough && <Verdict result={result} verdict={verdict} pitch={pitch} />}
    </div>
  );
}

function Verdict({ result, verdict, pitch }) {
  const { players, names, table } = result;

  // Clean text for the crew's WhatsApp group.
  const share = [
    `⚖️ Settle it: ${names.a} vs ${names.b}`,
    result.scope,
    "",
    ...table.map((row) => `${row.label}: ${row.a} / ${row.b}`),
    "",
    verdict,
    "",
    `${window.location.origin}/pitch/${pitch.id}`,
  ].join("\n");

  return (
    <>
      <section className="card stack">
        <p className="muted center">{result.scope}</p>
        <table className="versus">
          <thead>
            <tr>
              <th><Avatar user={players.a} size={44} /><br />{names.a}</th>
              <th></th>
              <th><Avatar user={players.b} size={44} /><br />{names.b}</th>
            </tr>
          </thead>
          <tbody>
            {table.map((row) => (
              <tr key={row.label}>
                <td><strong>{row.a}</strong></td>
                <td className="muted">{row.label}</td>
                <td><strong>{row.b}</strong></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card stack highlight">
        <h3>Star Boy's verdict</h3>
        {verdict ? (
          <p className="verdict">{verdict}</p>
        ) : (
          <p className="muted">
            <span className="pulse small">⭐</span> Star Boy is thinking it over… (up to a minute)
          </p>
        )}
      </section>

      {verdict && (
        <a className="button gold" href={whatsappLink(share)} target="_blank" rel="noreferrer">
          Share to WhatsApp
        </a>
      )}
    </>
  );
}
