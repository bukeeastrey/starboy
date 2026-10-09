import { useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { ErrorNote } from "./components.jsx";
import { uploadPhoto } from "./photos.js";

// A game's photos. The grid shows small thumbnails (loaded only as they
// scroll into view); tapping one opens the full photo.
export default function Gallery({ game, onChange }) {
  const [open, setOpen] = useState(null); // the photo shown full-screen
  const [uploading, setUploading] = useState(0); // how many are being sent
  const [error, setError] = useState("");
  const picker = useRef(null);

  async function addPhotos(event) {
    const files = [...event.target.files];
    event.target.value = ""; // so picking the same photo again still works
    setError("");
    setUploading(files.length);
    for (const file of files) {
      try {
        await uploadPhoto(`/api/games/${game.id}/photos`, file);
      } catch (err) {
        setError(err.message);
      }
      setUploading((left) => left - 1);
    }
    await onChange();
  }

  async function remove(photo) {
    if (!window.confirm("Delete this photo?")) return;
    try {
      await api(`/api/photos/${photo.id}`, { method: "DELETE" });
      setOpen(null);
      await onChange();
    } catch (err) {
      setError(err.message);
    }
  }

  if (game.photos.length === 0 && !game.can_add_photos) return null;

  return (
    <section className="stack">
      <h3>Photos{game.photos.length > 0 ? ` (${game.photos.length})` : ""}</h3>

      <div className="gallery">
        {game.photos.map((photo) => (
          <button key={photo.id} className="gallery-tile" onClick={() => setOpen(photo)}>
            <img src={photo.thumb} alt={`Match photo by ${photo.by}`} loading="lazy" decoding="async" />
          </button>
        ))}
        {game.can_add_photos && (
          <button className="gallery-tile gallery-add" onClick={() => picker.current.click()}
                  disabled={uploading > 0}>
            {uploading > 0 ? (
              <span>Sending {uploading}…</span>
            ) : (
              <>
                <strong>+</strong>
                <span>Add photos</span>
              </>
            )}
          </button>
        )}
      </div>
      {/* The real file picker is hidden; the tile above opens it. */}
      <input ref={picker} type="file" accept="image/*" multiple hidden onChange={addPhotos} />
      <ErrorNote error={error} />

      {open && <Lightbox photo={open} onClose={() => setOpen(null)} onDelete={remove} />}
    </section>
  );
}

// The full photo over the whole screen. Tap outside it, or Close, to go back.
function Lightbox({ photo, onClose, onDelete }) {
  useEffect(() => {
    const onKey = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="lightbox" onClick={onClose} role="dialog" aria-label="Photo">
      <img src={photo.full} alt={`Match photo by ${photo.by}`} onClick={(event) => event.stopPropagation()} />
      <div className="lightbox-bar" onClick={(event) => event.stopPropagation()}>
        <span className="muted">{photo.by ? `Photo: ${photo.by}` : ""}</span>
        {photo.can_delete && (
          <button className="link-button" onClick={() => onDelete(photo)}>Delete</button>
        )}
        <button className="button secondary" onClick={onClose}>Close</button>
      </div>
    </div>
  );
}
