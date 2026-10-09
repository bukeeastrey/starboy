// Small, cheap motion: numbers that count up, a gold burst, a live countdown.
// No animation library: a little JavaScript and CSS. Players who ask their
// phone for less motion get none of it (see prefers-reduced-motion below).

import { useEffect, useRef, useState } from "react";

function wantsLessMotion() {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}

// A number that counts up from 0 the first time it scrolls into view.
export function CountUp({ value, duration = 700 }) {
  const target = Number(value) || 0;
  const [shown, setShown] = useState(wantsLessMotion() ? target : 0);
  const element = useRef(null);
  const done = useRef(wantsLessMotion());

  useEffect(() => {
    // Already counted (or no motion wanted): just show the newest number.
    if (done.current) {
      setShown(target);
      return;
    }
    let frame;
    const watcher = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      watcher.disconnect();
      done.current = true;
      const started = performance.now();
      const step = (now) => {
        const progress = Math.min(1, (now - started) / duration);
        const eased = 1 - (1 - progress) ** 3; // fast at first, then settling
        setShown(Math.round(target * eased));
        if (progress < 1) frame = requestAnimationFrame(step);
      };
      frame = requestAnimationFrame(step);
    }, { threshold: 0.4 });
    watcher.observe(element.current);
    return () => {
      watcher.disconnect();
      cancelAnimationFrame(frame);
    };
  }, [target, duration]);

  return <span ref={element}>{shown}</span>;
}

// True the first time this browser sees `key`, false ever after. Used so a
// celebration plays once, not on every visit.
export function useFirstTime(key) {
  const [first] = useState(() => {
    if (!key) return false;
    try {
      if (localStorage.getItem(key)) return false;
      localStorage.setItem(key, "1");
      return true;
    } catch {
      return false; // private browsing: skip the celebration
    }
  });
  return first;
}

// A small burst of gold sparks from the middle of its parent (which must
// have position: relative). Pure CSS; it removes itself from view when done.
export function Burst() {
  if (wantsLessMotion()) return null;
  return (
    <span className="burst" aria-hidden="true">
      {Array.from({ length: 14 }, (_, i) => (
        <i key={i} style={{ "--angle": `${i * (360 / 14)}deg`, "--far": `${60 + (i % 3) * 22}px` }} />
      ))}
    </span>
  );
}

// "2d 04h 13m" until kickoff, ticking every second in the last hour.
export function Countdown({ to }) {
  const [now, setNow] = useState(Date.now());
  const left = new Date(to).getTime() - now;

  useEffect(() => {
    // Every second when it's close, every half minute when it's far.
    const timer = setInterval(() => setNow(Date.now()), left < 3600_000 ? 1000 : 30_000);
    return () => clearInterval(timer);
  }, [left < 3600_000]);

  if (left <= 0) return <span className="countdown live">Kickoff!</span>;

  const two = (n) => String(n).padStart(2, "0");
  const days = Math.floor(left / 86_400_000);
  const hours = Math.floor(left / 3_600_000) % 24;
  const minutes = Math.floor(left / 60_000) % 60;
  const seconds = Math.floor(left / 1000) % 60;
  const parts = days > 0
    ? [[days, "d"], [two(hours), "h"], [two(minutes), "m"]]
    : hours > 0
      ? [[hours, "h"], [two(minutes), "m"]]
      : [[two(minutes), "m"], [two(seconds), "s"]];

  return (
    <span className="countdown" aria-label="Time until kickoff">
      {parts.map(([number, unit]) => (
        <span key={unit}><b>{number}</b>{unit}</span>
      ))}
    </span>
  );
}
