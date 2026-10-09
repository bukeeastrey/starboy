import { useState } from "react";
import { api } from "./api.js";
import { ErrorNote } from "./components.jsx";
import { statLine } from "./game-parts.jsx";

// The blocks + tackles answer is a bucket, not an exact count.
export const DEFENDING_BUCKETS = ["0", "1-2", "3-5", "6+"];
const COUNTS = [0, 1, 2, 3];

// "Tap my stats": a report made with buttons, one question at a time.
// The same flow the Telegram bot offers, for players who don't want to talk.
//   goals -> assists -> defending (keepers: saves + clean sheet) -> MOTM -> summary
export default function TapFlow({ game, me, onSubmitted, onCancel }) {
  const keeper = me.position === "GK";
  const steps = keeper
    ? ["goals", "assists", "saves", "clean_sheet", "motm"]
    : ["goals", "assists", "defending", "motm"];

  const [answers, setAnswers] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // The first question without an answer, or undefined when all are answered.
  const step = steps.find((name) => !(name in answers));
  const others = game.players.in.filter((player) => player.id !== me.id);
  const answer = (name, value) => setAnswers({ ...answers, [name]: value });

  async function submit() {
    setBusy(true);
    setError("");
    try {
      await api(`/api/games/${game.id}/claim`, {
        method: "POST",
        body: {
          source: "buttons",
          motm_vote_id: answers.motm || "",
          edit: new URLSearchParams(window.location.search).has("edit"),
          stats: {
            goals: answers.goals, assists: answers.assists,
            saves: answers.saves ?? null, clean_sheet: answers.clean_sheet ?? null,
            defending: answers.defending ?? null,
          },
        },
      });
      onSubmitted();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  if (!step) {
    const voted = others.find((player) => player.id === answers.motm);
    return (
      <div className="tap-step">
        <p className="tap-progress">Your game</p>
        <p className="tap-summary">{statLine(answers)}</p>
        {voted && <p className="muted">MOTM vote: {voted.nickname || voted.name}</p>}
        <ErrorNote error={error} />
        <button className="button big" onClick={submit} disabled={busy}>
          {busy ? "Sending…" : "Submit"}
        </button>
        <button className="link-button" onClick={() => setAnswers({})}>Start again</button>
      </div>
    );
  }

  return (
    <div className="tap-step">
      <p className="tap-progress">
        Question {steps.indexOf(step) + 1} of {steps.length}
      </p>

      {["goals", "assists", "saves"].includes(step) && (
        <CountQuestion
          title={{ goals: "Goals?", assists: "Assists?", saves: "Saves?" }[step]}
          onAnswer={(value) => answer(step, value)}
        />
      )}

      {step === "defending" && (
        <>
          <h3 className="tap-question">Blocks + tackles?</h3>
          <div className="tap-options">
            {DEFENDING_BUCKETS.map((bucket) => (
              <button key={bucket} className="tap-option" onClick={() => answer("defending", bucket)}>
                {bucket.replace("-", "–")}
              </button>
            ))}
          </div>
        </>
      )}

      {step === "clean_sheet" && (
        <>
          <h3 className="tap-question">Clean sheet?</h3>
          <div className="tap-options">
            <button className="tap-option" onClick={() => answer("clean_sheet", true)}>Yes</button>
            <button className="tap-option" onClick={() => answer("clean_sheet", false)}>No</button>
          </div>
        </>
      )}

      {step === "motm" && (
        <>
          <h3 className="tap-question">Man of the match?</h3>
          <div className="tap-options names">
            {others.map((player) => (
              <button key={player.id} className="tap-option" onClick={() => answer("motm", player.id)}>
                {player.nickname || player.name.split(" ")[0]}
              </button>
            ))}
            <button className="tap-option quiet" onClick={() => answer("motm", "")}>Skip</button>
          </div>
        </>
      )}

      <button className="link-button" onClick={onCancel}>Use a voice note instead</button>
    </div>
  );
}

// 0 / 1 / 2 / 3 / 4+ , where 4+ asks for the exact number.
function CountQuestion({ title, onAnswer }) {
  const [more, setMore] = useState(false);
  const [exact, setExact] = useState("");
  const number = Number(exact);
  const valid = exact !== "" && Number.isInteger(number) && number >= 4 && number <= 20;

  return (
    <>
      <h3 className="tap-question">{title}</h3>
      {more ? (
        <form
          className="tap-exact"
          onSubmit={(event) => { event.preventDefault(); if (valid) onAnswer(number); }}
        >
          <input
            type="number" inputMode="numeric" min="4" max="20" autoFocus
            value={exact} onChange={(event) => setExact(event.target.value)}
            placeholder="How many?"
          />
          <button className="button" disabled={!valid}>OK</button>
        </form>
      ) : (
        <div className="tap-options">
          {COUNTS.map((count) => (
            <button key={count} className="tap-option" onClick={() => onAnswer(count)}>{count}</button>
          ))}
          <button className="tap-option" onClick={() => setMore(true)}>4+</button>
        </div>
      )}
    </>
  );
}
