import { useState } from "react";
import { api } from "./api.js";
import { Avatar } from "./components.jsx";
import { Link } from "./router.jsx";

// The four reactions, in the order they are shown.
const REACTIONS = [
  ["fire", "🔥"],
  ["ball", "⚽"],
  ["clap", "👏"],
  ["laugh", "😂"],
];

const HOW_MANY_AT_FIRST = 4;

// The highlights feed on a pitch page. Each card is made by the backend from
// confirmed stats (see backend/app/moments.py); here we only show them.
export default function Moments({ moments }) {
  const [showAll, setShowAll] = useState(false);
  if (moments.length === 0) return null;
  const shown = showAll ? moments : moments.slice(0, HOW_MANY_AT_FIRST);

  return (
    <section className="stack">
      <h3>Moments</h3>
      <div className="moments">
        {shown.map((moment) => <MomentCard key={moment.id} moment={moment} />)}
      </div>
      {!showAll && moments.length > HOW_MANY_AT_FIRST && (
        <button className="link-button" onClick={() => setShowAll(true)}>
          Show {moments.length - HOW_MANY_AT_FIRST} more
        </button>
      )}
    </section>
  );
}

function MomentCard({ moment }) {
  // Kept here so a tap shows at once; the backend's answer then corrects it.
  const [reactions, setReactions] = useState(moment.reactions);
  const [mine, setMine] = useState(moment.my_reaction);

  async function react(name) {
    try {
      const updated = await api(`/api/moments/${moment.id}/react`, {
        method: "POST", body: { reaction: name },
      });
      setReactions(updated.reactions);
      setMine(updated.my_reaction);
    } catch {
      // A failed reaction isn't worth an error message; the counts just stay.
    }
  }

  const body = (
    <>
      {moment.photo && (
        <img className="moment-photo" src={moment.photo.thumb} alt="" loading="lazy" decoding="async" />
      )}
      <div className="moment-text">
        <span className="moment-when">{moment.when}</span>
        <strong className="moment-title">{moment.title}</strong>
        <p>{moment.line}</p>
      </div>
    </>
  );

  return (
    <article className={`moment moment-${moment.kind}`}>
      {/* A moment from a game opens that game. */}
      {moment.game_id ? (
        <Link to={`/game/${moment.game_id}`} className="moment-body">{body}</Link>
      ) : (
        <div className="moment-body">{body}</div>
      )}
      <footer className="moment-foot">
        {moment.player && (
          <Link to={`/player/${moment.player.id}`} className="moment-player">
            <Avatar user={moment.player} size={28} />
            <span>{moment.player.nickname || moment.player.name.split(" ")[0]}</span>
          </Link>
        )}
        <div className="reactions">
          {REACTIONS.map(([name, emoji]) => (
            <button
              key={name}
              className={mine === name ? "reaction mine" : "reaction"}
              onClick={() => react(name)}
              aria-label={`React ${emoji}`}
              aria-pressed={mine === name}
            >
              <span>{emoji}</span>
              {reactions[name] > 0 && <b>{reactions[name]}</b>}
            </button>
          ))}
        </div>
      </footer>
    </article>
  );
}
