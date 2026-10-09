import { useState } from "react";
import { api } from "../api.js";
import { ErrorNote } from "../components.jsx";
import { Link } from "../router.jsx";

export default function SignIn({ onSignedIn }) {
  const [phone, setPhone] = useState("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      onSignedIn(await api("/api/auth/signin", { method: "POST", body: { phone, pin } }));
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <form className="form" onSubmit={submit}>
      <h2>Welcome back</h2>

      <label>
        Phone number
        <input
          type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
          placeholder="0803 123 4567" autoComplete="tel" required
        />
      </label>

      <label>
        Your 4-digit PIN
        <input
          type="password" inputMode="numeric" maxLength={4}
          value={pin} onChange={(e) => setPin(e.target.value)}
          autoComplete="current-password" required
        />
      </label>

      <ErrorNote error={error} />
      <button className="button big" disabled={busy}>
        {busy ? "Signing in…" : "Sign in"}
      </button>
      <p className="center">
        New here? <Link to="/signup">Join Star Boy</Link>
      </p>
    </form>
  );
}
