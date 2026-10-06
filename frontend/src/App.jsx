import { useEffect, useState } from "react";
import { api } from "./api.js";
import { Avatar, Loading } from "./components.jsx";
import { Link, matchRoute, navigate, usePath } from "./router.jsx";
import Game from "./pages/Game.jsx";
import Home from "./pages/Home.jsx";
import NewGame from "./pages/NewGame.jsx";
import Pitch from "./pages/Pitch.jsx";
import Pitches from "./pages/Pitches.jsx";
import SignIn from "./pages/SignIn.jsx";
import SignUp from "./pages/SignUp.jsx";
import Welcome from "./pages/Welcome.jsx";

// The screens for signed-in players. ":id" parts are passed to the screen as props.
const ROUTES = [
  ["/", Home],
  ["/pitches", Pitches],
  ["/pitch/:id", Pitch],
  ["/pitch/:id/new-game", NewGame],
  ["/game/:id", Game],
];

// Where to go after signing in (e.g. the game link someone sent on WhatsApp).
const NEXT_KEY = "starboy_next";

export default function App() {
  const path = usePath();
  // undefined = still checking, null = signed out, otherwise the user.
  const [user, setUser] = useState(undefined);

  useEffect(() => {
    api("/api/me")
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  function onSignedIn(newUser) {
    setUser(newUser);
    const next = sessionStorage.getItem(NEXT_KEY) || "/";
    sessionStorage.removeItem(NEXT_KEY);
    navigate(next, { replace: true });
  }

  async function signOut() {
    await api("/api/auth/signout", { method: "POST" }).catch(() => {});
    setUser(null);
    navigate("/");
  }

  let screen;
  if (user === undefined) {
    screen = <Loading />;
  } else if (user === null) {
    if (path === "/signup") screen = <SignUp onSignedIn={onSignedIn} />;
    else if (path === "/signin") screen = <SignIn onSignedIn={onSignedIn} />;
    else {
      // Remember the page they wanted, then show the welcome screen.
      if (path !== "/") sessionStorage.setItem(NEXT_KEY, path);
      screen = <Welcome invited={path.startsWith("/game/")} />;
    }
  } else {
    screen = <NotFound />;
    for (const [pattern, Screen] of ROUTES) {
      const params = matchRoute(pattern, path);
      if (params) {
        // key = path, so moving between two pitches starts a fresh screen.
        screen = <Screen key={path} user={user} {...params} />;
        break;
      }
    }
  }

  return (
    <div className="app">
      {user && (
        <header className="topbar">
          <Link to="/" className="brand">⭐ Star Boy</Link>
          <button className="link-button" onClick={signOut}>Sign out</button>
          <Avatar user={user} size={34} />
        </header>
      )}
      <main className="main">{screen}</main>
      <footer className="badge">
        AI: Gemma + Whisper, open models running on Star Boy's own server
      </footer>
    </div>
  );
}

function NotFound() {
  return (
    <div className="center">
      <h2>Offside! 🚩</h2>
      <p className="muted">We can't find that page.</p>
      <Link to="/" className="button">Back home</Link>
    </div>
  );
}
