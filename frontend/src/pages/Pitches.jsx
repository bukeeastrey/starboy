import { useState } from "react";
import { api } from "../api.js";
import { ErrorNote, Loading, useLoad } from "../components.jsx";
import { navigate } from "../router.jsx";
import { PitchRow } from "./Home.jsx";

// "Find a pitch": every pitch, plus a form to add a new one.
export default function Pitches() {
  const { data: pitches, error } = useLoad(() => api("/api/pitches"), []);
  const [adding, setAdding] = useState(false);

  return (
    <div className="stack">
      <h2>Find a pitch 🏟️</h2>
      <ErrorNote error={error} />
      {!pitches && !error && <Loading />}
      {pitches?.map((pitch) => <PitchRow key={pitch.id} pitch={pitch} />)}

      {adding ? (
        <AddPitchForm onCancel={() => setAdding(false)} />
      ) : (
        <button className="button secondary" onClick={() => setAdding(true)}>
          + Add a pitch
        </button>
      )}
    </div>
  );
}

function AddPitchForm({ onCancel }) {
  const [form, setForm] = useState({ name: "", area: "", maps_url: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (field) => (event) => setForm({ ...form, [field]: event.target.value });

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const pitch = await api("/api/pitches", { method: "POST", body: form });
      navigate(`/pitch/${pitch.id}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <form className="form card" onSubmit={submit}>
      <h3>Add a pitch</h3>
      <label>
        Name
        <input value={form.name} onChange={set("name")} placeholder="Parklane Football Pitch" required />
      </label>
      <label>
        Area or landmark
        <input value={form.area} onChange={set("area")} placeholder="Behind the big mango tree" />
      </label>
      <label>
        Google Maps link <span className="muted">(optional)</span>
        <input type="url" value={form.maps_url} onChange={set("maps_url")} placeholder="https://maps.app.goo.gl/…" />
      </label>
      <ErrorNote error={error} />
      <button className="button" disabled={busy}>{busy ? "Adding…" : "Add pitch"}</button>
      <button type="button" className="link-button" onClick={onCancel}>Cancel</button>
    </form>
  );
}
