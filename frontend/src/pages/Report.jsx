import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { ErrorNote, Loading, useLoad } from "../components.jsx";
import { canRecord, startRecording } from "../recorder.js";
import TapFlow, { DEFENDING_BUCKETS } from "../TapFlow.jsx";
import { Link, navigate } from "../router.jsx";

const MAX_SECONDS = 90;
const HOLD_MS = 500; // pressing longer than this counts as "hold to talk"
const POLL_MS = 2000;

// What to say while the AI job is in each stage.
const STAGE_TEXT = {
  queued: "Star Boy is getting ready…",
  listening: "Star Boy is listening to your voice note… 🎧",
  thinking: "Working out your stats… 🧮",
  warming_up: "Star Boy is warming up (first time can take a few minutes) 🏃",
};

// "How was your game?" The screen moves through these steps:
//   record (or type) -> processing -> review -> back to the game page
export default function Report({ id, user }) {
  const { data: game, error } = useLoad(() => api(`/api/games/${id}`), [id]);
  // "?job=<id>" in the address: the player already sent a voice note on
  // Telegram and tapped "Edit on web ✏️", so go straight to that result.
  const [fromTelegram] = useState(() => new URLSearchParams(window.location.search).get("job"));
  const [step, setStep] = useState(fromTelegram ? "processing" : "record");
  const [jobId, setJobId] = useState(fromTelegram);
  const [result, setResult] = useState(null); // { transcript, stats, unclear }
  const [problem, setProblem] = useState("");
  const [wasTyped, setWasTyped] = useState(false);

  // Send the voice note (a Blob) or the typed text; the backend queues an AI job.
  async function send(what) {
    setProblem("");
    setWasTyped(typeof what === "string");
    setStep("processing");
    try {
      let job;
      if (typeof what === "string") {
        job = await api(`/api/games/${id}/report/text`, { method: "POST", body: { text: what } });
      } else {
        const form = new FormData();
        form.append("file", what, "voice-note");
        job = await api(`/api/games/${id}/report/audio`, { method: "POST", body: form });
      }
      setJobId(job.job_id);
    } catch (err) {
      setProblem(err.message);
      setStep("record");
    }
  }

  function onJobDone(job) {
    setJobId(null);
    if (job.status === "error") {
      setProblem(job.error);
      setStep("record");
    } else if (job.result.empty) {
      setProblem("I didn't catch that. Try again or type it.");
      setStep("record");
    } else {
      setResult({ ...job.result, typed: wasTyped });
      setStep("review");
    }
  }

  if (error) return <ErrorNote error={error} />;
  if (!game) return <Loading />;
  if (!game.can_report) {
    return (
      <div className="stack center">
        <p className="card">
          You can tell Star Boy about this game after kickoff, once you're marked “in”.
        </p>
        <Link to={`/game/${id}`} className="button">Back to the game</Link>
      </div>
    );
  }

  return (
    <div className="stack">
      <div>
        <h2>How was your game? 🎙️</h2>
        <p className="muted">{game.pitch.name} · {game.kickoff_label}</p>
      </div>
      <ErrorNote error={problem} />

      {step === "record" && <Recorder onSend={send} onTap={() => setStep("tap")} />}
      {step === "tap" && (
        <TapFlow
          game={game} me={user}
          onCancel={() => setStep("record")}
          onSubmitted={() => navigate(`/game/${id}`)}
        />
      )}
      {step === "processing" && <Processing jobId={jobId} onDone={onJobDone} />}
      {step === "review" && (
        <Review
          game={game} result={result} me={user}
          onRedo={() => setStep("record")}
          onSubmitted={() => navigate(`/game/${id}`)}
        />
      )}
    </div>
  );
}

// --- Step 1: talk (or type) ------------------------------------------------

function Recorder({ onSend, onTap }) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [typing, setTyping] = useState(!canRecord());
  const [text, setText] = useState("");
  const [error, setError] = useState("");

  const recorder = useRef(null); // the running recording, if any
  const pressedAt = useRef(0); // when the finger went down
  const starting = useRef(false); // true while the browser asks for the mic

  // Count the seconds while recording.
  useEffect(() => {
    if (!recording) return;
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [recording]);

  // Stop by itself at the limit.
  useEffect(() => {
    if (recording && seconds >= MAX_SECONDS) finish();
  });

  // Leaving the screen switches the microphone off.
  useEffect(() => () => { recorder.current?.stop(); }, []);

  async function begin() {
    if (starting.current || recorder.current) return;
    starting.current = true;
    setError("");
    try {
      recorder.current = await startRecording();
      setSeconds(0);
      setRecording(true);
    } catch {
      setError("Star Boy can't use your microphone. Allow it in your browser, or type it instead.");
    }
    starting.current = false;
  }

  async function finish() {
    if (!recorder.current) return;
    const current = recorder.current;
    recorder.current = null;
    setRecording(false);
    onSend(await current.stop());
  }

  // One button, two ways to use it:
  //   hold it down, talk, let go          -> sends when you let go
  //   tap once, talk, tap again           -> sends on the second tap
  function onPress() {
    if (recording) {
      finish();
    } else {
      pressedAt.current = Date.now();
      begin();
    }
  }

  function onRelease() {
    const held = Date.now() - pressedAt.current;
    if (recording && pressedAt.current && held > HOLD_MS) finish();
    pressedAt.current = 0;
  }

  if (typing) {
    return (
      <form
        className="form"
        onSubmit={(event) => { event.preventDefault(); onSend(text); }}
      >
        <label>
          Tell Star Boy how your game went
          <textarea
            rows={4} value={text} maxLength={1000}
            onChange={(event) => setText(event.target.value)}
            placeholder="We won 5-3. I scored two and assisted Emeka once."
          />
        </label>
        <button className="button big" disabled={text.trim().length < 3}>Send to Star Boy</button>
        {canRecord() && (
          <button type="button" className="link-button" onClick={() => setTyping(false)}>
            Use a voice note instead
          </button>
        )}
      </form>
    );
  }

  const left = MAX_SECONDS - seconds;
  return (
    <div className="stack center">
      <button
        className={recording ? "mic recording" : "mic"}
        onPointerDown={onPress}
        onPointerUp={onRelease}
        onPointerLeave={onRelease}
        onContextMenu={(event) => event.preventDefault()} // no long-press menu on phones
        aria-label={recording ? "Stop recording" : "Start recording"}
      >
        {recording ? "⏹" : "🎙️"}
      </button>
      {recording ? (
        <p>
          <strong className="timer">0:{String(seconds).padStart(2, "0")}</strong>
          <br />
          <span className="muted">
            {left <= 10 ? `${left} seconds left` : "Let go or tap to send"}
          </span>
        </p>
      ) : (
        <p>
          <strong>Hold to tell Star Boy how your game went</strong>
          <br />
          <span className="muted">
            or tap once to start. Say your goals, your assists, anything worth telling.
          </span>
        </p>
      )}
      <ErrorNote error={error} />
      {!recording && (
        <>
          <button className="button secondary" onClick={onTap}>Tap my stats instead</button>
          <button className="link-button" onClick={() => setTyping(true)}>Type it instead</button>
        </>
      )}
    </div>
  );
}

// --- Step 2: wait for the AI -------------------------------------------------

function Processing({ jobId, onDone }) {
  const [job, setJob] = useState(null);

  // Ask the backend every 2 seconds until the job is done.
  useEffect(() => {
    if (!jobId) return;
    let stopped = false;
    let timer;

    async function poll() {
      try {
        const latest = await api(`/api/jobs/${jobId}`);
        if (stopped) return;
        if (latest.status === "done" || latest.status === "error") {
          onDone(latest);
          return;
        }
        setJob(latest);
      } catch {
        // A network blip: just try again at the next poll.
      }
      timer = setTimeout(poll, POLL_MS);
    }
    poll();

    return () => {
      stopped = true;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  let text = STAGE_TEXT[job?.stage] ?? "Sending to Star Boy…";
  if (job?.status === "queued" && job.ahead > 0) {
    text = `Star Boy is busy with ${job.ahead} other ${job.ahead === 1 ? "report" : "reports"}. You're next…`;
  }

  return (
    <div className="card stack center">
      <div className="pulse">⭐</div>
      <p><strong>{text}</strong></p>
      <p className="muted">
        This can take up to a minute. Open models do the listening: Whisper and Gemma.
      </p>
    </div>
  );
}

// --- Step 3: "Here's what I heard" -------------------------------------------

function Review({ game, result, me, onRedo, onSubmitted }) {
  const [stats, setStats] = useState(result.stats);
  const [assisted, setAssisted] = useState(
    new Set(result.stats.assisted_players.map((player) => player.id))
  );
  const [keeper, setKeeper] = useState(
    result.stats.saves !== null || result.stats.clean_sheet !== null
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const set = (field) => (value) => setStats({ ...stats, [field]: value });
  const teammates = game.players.in.filter((player) => player.id !== me.id);

  const [motm, setMotm] = useState("");

  function toggleAssisted(playerId) {
    const next = new Set(assisted);
    if (next.has(playerId)) next.delete(playerId);
    else next.add(playerId);
    setAssisted(next);
  }

  async function submit() {
    setBusy(true);
    setError("");
    try {
      await api(`/api/games/${game.id}/claim`, {
        method: "POST",
        body: {
          transcript: result.transcript,
          source: result.typed ? "text" : "voice",
          motm_vote_id: motm,
          assisted_player_ids: [...assisted],
          // "?edit=1" in the address = changing a report teammates already confirmed.
          edit: new URLSearchParams(window.location.search).has("edit"),
          // Not a keeper today = no keeper stats.
          stats: keeper ? stats : { ...stats, saves: null, clean_sheet: null },
        },
      });
      onSubmitted();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <h3>Here's what I heard</h3>
      <blockquote className="card quote">“{result.transcript}”</blockquote>

      {result.unclear.length > 0 && (
        <p className="card unsure">
          🤔 I wasn't sure about: {result.unclear.join("; ")}. Check the numbers below.
        </p>
      )}

      <div className="card stack">
        <Stepper label="⚽ Goals" value={stats.goals} onChange={set("goals")} />
        <Stepper label="🎯 Assists" value={stats.assists} onChange={set("assists")} />

        <label className="check">
          <input type="checkbox" checked={keeper} onChange={() => setKeeper(!keeper)} />
          I was in goal 🧤
        </label>
        {keeper && (
          <>
            <Stepper label="🧤 Saves" value={stats.saves} onChange={set("saves")} />
            <label className="check">
              <input
                type="checkbox" checked={stats.clean_sheet === true}
                onChange={() => set("clean_sheet")(stats.clean_sheet !== true)}
              />
              Clean sheet (dem no score us)
            </label>
          </>
        )}
      </div>

      {!keeper && (
        <div className="card stack">
          <strong>Blocks + tackles?</strong>
          <div className="choices">
            {DEFENDING_BUCKETS.map((bucket) => (
              <button
                key={bucket} type="button"
                className={stats.defending === bucket ? "choice selected" : "choice"}
                onClick={() => set("defending")(stats.defending === bucket ? null : bucket)}
              >
                {bucket.replace("-", "–")}
              </button>
            ))}
          </div>
        </div>
      )}

      {teammates.length > 0 && (
        <div className="card stack">
          <strong>Man of the match?</strong>
          <div className="choices">
            {teammates.map((player) => (
              <button
                key={player.id} type="button"
                className={motm === player.id ? "choice selected" : "choice"}
                onClick={() => setMotm(motm === player.id ? "" : player.id)}
              >
                {player.nickname || player.name.split(" ")[0]}
              </button>
            ))}
          </div>
        </div>
      )}

      {teammates.length > 0 && (
        <div className="card stack">
          <strong>Who did you assist?</strong>
          <div className="choices">
            {teammates.map((player) => (
              <button
                key={player.id} type="button"
                className={assisted.has(player.id) ? "choice selected" : "choice"}
                onClick={() => toggleAssisted(player.id)}
              >
                {player.nickname || player.name}
              </button>
            ))}
          </div>
        </div>
      )}

      <label className="form">
        <strong>Your highlight</strong>
        <input
          value={stats.highlight} maxLength={120}
          onChange={(event) => set("highlight")(event.target.value)}
          placeholder="One line about your game"
        />
      </label>

      <ErrorNote error={error} />
      <button className="button big" onClick={submit} disabled={busy}>
        {busy ? "Sending…" : "Looks right, submit ✅"}
      </button>
      <button className="link-button" onClick={onRedo}>Start again</button>
      <p className="muted center">
        Your stats count once teammates from this game confirm them.
      </p>
    </div>
  );
}

// A number with − and + buttons. null means "not said" and shows as a dash.
function Stepper({ label, value, onChange }) {
  return (
    <div className="stepper">
      <span>{label}</span>
      <button
        type="button" aria-label={`Less ${label}`}
        onClick={() => onChange(value === null ? 0 : Math.max(0, value - 1))}
      >
        −
      </button>
      <strong>{value ?? "–"}</strong>
      <button
        type="button" aria-label={`More ${label}`}
        onClick={() => onChange(Math.min(20, (value ?? 0) + 1))}
      >
        +
      </button>
    </div>
  );
}
