import { useEffect, useState } from "react";
import { Wordmark } from "../Crest.jsx";
import { Link } from "../router.jsx";

// Three things football people really said. Only well-documented quotes.
const QUOTES = [
  {
    text: "Playing football is very simple, but playing simple football is the hardest thing there is.",
    who: "Johan Cruyff",
  },
  {
    text: "Some people believe football is a matter of life and death. I can assure you it is much, much more important than that.",
    who: "Bill Shankly",
  },
  {
    text: "Success is no accident. It is hard work, perseverance, learning, studying, sacrifice and most of all, love of what you are doing.",
    who: "Pelé",
  },
];
const QUOTE_SECONDS = 8;

const STEPS = [
  ["Find your pitch", "Register where your people play, so they can call you up."],
  ["Get the reminder", "Invites and kickoff reminders land on Telegram. One tap: you dey come?"],
  ["Tell Star Boy", "After the game, send a voice note. Your goals go on the pitch leaderboard once teammates confirm."],
];

// The first screen for someone who is not signed in.
// "invited" is true when they opened a game link a friend sent them.
export default function Welcome({ invited }) {
  return (
    <div className="landing">
      <section className="hero">
        {/* The photo is in the repo (public/img), in two sizes: phones get the small one. */}
        <img
          className="hero-photo"
          src="/img/hero.jpg"
          srcSet="/img/hero-800.jpg 800w, /img/hero.jpg 1400w"
          sizes="100vw"
          alt="Two players chase the ball across a red-earth pitch in Nigeria at sunset, dust rising at their feet."
          fetchpriority="high"
        />
        <div className="hero-inner">
          <Wordmark size={36} />
          <h1>
            Comot for room.
            <br />
            <em>Come play ball.</em>
          </h1>
          <p className="hero-sub">
            Pickup football at your pitch: who's in, when's kickoff, and who really
            scored. Settled by your own teammates.
          </p>
          {invited && (
            <p className="hero-invite">
              Your people dey call you for football. Join to answer the invite.
            </p>
          )}
          <div className="hero-actions">
            <Link to="/signup" className="button gold big">Join Star Boy</Link>
            <Link to="/signin" className="link-button">I already have an account</Link>
          </div>
        </div>
      </section>

      <div className="landing-body">
        <QuoteRotator />

        <section className="stack">
          <h3>How it works</h3>
          <ol className="steps">
            {STEPS.map(([title, text], index) => (
              <li key={title}>
                <span className="step-number">0{index + 1}</span>
                <strong>{title}</strong>
                <p>{text}</p>
              </li>
            ))}
          </ol>
          <Link to="/signup" className="button big">Get on the team sheet</Link>
        </section>

        <footer className="badge">
          AI: Gemma + Whisper, open-weight models
          <br />
          Photo:{" "}
          <a
            href="https://www.pexels.com/photo/youth-playing-football-in-nigeria-at-sunset-30449603/"
            target="_blank" rel="noreferrer"
          >
            Kenechukwu Emmanuel / Pexels
          </a>
        </footer>
      </div>
    </div>
  );
}

// One quote at a time, changing every few seconds. Tap a line to jump.
function QuoteRotator() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => setIndex((index + 1) % QUOTES.length), QUOTE_SECONDS * 1000);
    return () => clearTimeout(timer);
  }, [index]);

  const quote = QUOTES[index];
  return (
    <section>
      {/* key = index, so the fade-in animation replays for each new quote */}
      <div className="quote-box" key={index}>
        <blockquote>“{quote.text}”</blockquote>
        <cite>{quote.who}</cite>
      </div>
      <div className="quote-dots">
        {QUOTES.map((item, i) => (
          <button
            key={item.who}
            aria-label={`Quote from ${item.who}`}
            aria-current={i === index}
            onClick={() => setIndex(i)}
          />
        ))}
      </div>
    </section>
  );
}
