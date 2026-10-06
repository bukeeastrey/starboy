import { useState } from "react";
import { api } from "../api.js";
import { ErrorNote } from "../components.jsx";
import { Link } from "../router.jsx";

const POSITIONS = ["GK", "DEF", "MID", "FWD", "Anywhere"];

export default function SignUp({ onSignedIn }) {
  const [form, setForm] = useState({
    name: "", nickname: "", phone: "", position: "Anywhere", pin: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // Change one field of the form, keep the others.
  const set = (field) => (event) => setForm({ ...form, [field]: event.target.value });

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      onSignedIn(await api("/api/auth/signup", { method: "POST", body: form }));
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <form className="form" onSubmit={submit}>
      <h2>Join Star Boy ⭐</h2>

      <label>
        Your name
        <input value={form.name} onChange={set("name")} autoComplete="name" required />
      </label>

      <label>
        Nickname <span className="muted">(optional, wetin dem dey call you for pitch?)</span>
        <input value={form.nickname} onChange={set("nickname")} />
      </label>

      <label>
        Phone number <span className="muted">(private, nobody else sees it)</span>
        <input
          type="tel" value={form.phone} onChange={set("phone")}
          placeholder="0803 123 4567" autoComplete="tel" required
        />
      </label>

      <fieldset>
        <legend>Where do you like to play?</legend>
        <div className="choices">
          {POSITIONS.map((position) => (
            <button
              type="button" key={position}
              className={form.position === position ? "choice selected" : "choice"}
              onClick={() => setForm({ ...form, position })}
            >
              {position}
            </button>
          ))}
        </div>
      </fieldset>

      <label>
        Choose a 4-digit PIN
        <input
          type="password" inputMode="numeric" pattern="\d{4}" maxLength={4}
          value={form.pin} onChange={set("pin")} autoComplete="new-password" required
        />
      </label>

      <ErrorNote error={error} />
      <button className="button big" disabled={busy}>
        {busy ? "Creating your account…" : "Let's play ⚽"}
      </button>
      <p className="center">
        <Link to="/signin">I already have an account</Link>
      </p>
    </form>
  );
}
