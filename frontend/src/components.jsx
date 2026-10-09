// Small pieces used on several screens.

import { useCallback, useEffect, useState } from "react";

const AVATAR_COLOURS = [
  "#0e5a3a", "#b4451f", "#1f5fb4", "#7a3fb0", "#b0863f", "#1f8a8a", "#b03f6c", "#4a6b1f",
];

// A circle with the player's profile photo, or their initials if they have
// none. The colour behind the initials is picked from their id, so the same
// player always gets the same colour.
export function Avatar({ user, size = 40 }) {
  if (user.photo) {
    return (
      <img
        className="avatar" src={user.photo} alt="" width={size} height={size}
        style={{ width: size, height: size }} loading="lazy" decoding="async"
      />
    );
  }
  const initials = user.name
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("");
  let sum = 0;
  for (const char of user.id) sum += char.charCodeAt(0);
  const style = {
    width: size,
    height: size,
    fontSize: size * 0.4,
    background: AVATAR_COLOURS[sum % AVATAR_COLOURS.length],
  };
  return (
    <span className="avatar" style={style} aria-hidden="true">
      {initials}
    </span>
  );
}

// "Tunde Bello" plus the nickname in quotes, if there is one.
export function PlayerName({ user }) {
  return (
    <span className="player-name">
      {user.name}
      {user.nickname && <span className="muted"> “{user.nickname}”</span>}
    </span>
  );
}

export function ErrorNote({ error }) {
  if (!error) return null;
  return <p className="error" role="alert">{error}</p>;
}

export function Loading({ text = "Loading…" }) {
  return <p className="muted center">{text}</p>;
}

// Load something from the backend when a screen opens.
// Returns { data, error, reload }. data is null while loading.
export function useLoad(loader, deps) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const reload = useCallback(() => {
    return loader()
      .then((result) => {
        setData(result);
        setError("");
      })
      .catch((err) => setError(err.message));
  }, deps);

  useEffect(() => {
    setData(null);
    reload();
  }, [reload]);

  return { data, error, reload };
}
