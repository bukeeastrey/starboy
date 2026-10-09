import { useEffect, useState } from "react";
import { ErrorNote } from "./components.jsx";

// A matchday poster for WhatsApp Status: a tall image (1080 x 1920) with the
// crest, the pitch, the date and who's in. It is drawn right here in the
// browser on a <canvas>, so there is no image library and nothing is uploaded.

const WIDTH = 1080;
const HEIGHT = 1920;
const NIGHT = "#050d09";
const CHALK = "#f1f4ee";
const DIM = "#9aaca1";
const GOLD = "#f5c518";
const LINE = "rgba(241, 244, 238, 0.16)";

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = src;
  });
}

// Break text into lines that fit a width (canvas doesn't wrap text itself).
function wrap(ctx, text, maxWidth) {
  const lines = [];
  let line = "";
  for (const word of text.split(/\s+/)) {
    const longer = line ? `${line} ${word}` : word;
    if (line && ctx.measureText(longer).width > maxWidth) {
      lines.push(line);
      line = word;
    } else {
      line = longer;
    }
  }
  if (line) lines.push(line);
  return lines;
}

// Draw the poster and return it as a PNG file (a Blob).
export async function drawPoster(game) {
  // The page's fonts must be ready before the canvas can use them.
  await Promise.all([
    document.fonts.load("400 100px Anton"),
    document.fonts.load("600 40px Barlow"),
    document.fonts.load("700 40px Barlow"),
  ]);
  const crest = await loadImage("/crest.svg");

  const canvas = document.createElement("canvas");
  canvas.width = WIDTH;
  canvas.height = HEIGHT;
  const ctx = canvas.getContext("2d");
  const margin = 90;

  // The night sky, with a floodlight glow from the top.
  ctx.fillStyle = NIGHT;
  ctx.fillRect(0, 0, WIDTH, HEIGHT);
  const glow = ctx.createRadialGradient(WIDTH / 2, -100, 0, WIDTH / 2, -100, 1300);
  glow.addColorStop(0, "rgba(40, 110, 76, 0.75)");
  glow.addColorStop(1, "rgba(5, 13, 9, 0)");
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, WIDTH, HEIGHT);

  // Pitch markings in chalk: a touchline frame, the halfway line, the centre circle.
  ctx.strokeStyle = LINE;
  ctx.lineWidth = 3;
  ctx.strokeRect(40, 40, WIDTH - 80, HEIGHT - 80);
  ctx.beginPath();
  ctx.arc(WIDTH / 2, HEIGHT - 40, 330, Math.PI, 0);
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(WIDTH / 2, HEIGHT - 40, 8, 0, Math.PI * 2);
  ctx.fillStyle = LINE;
  ctx.fill();

  // The crest and the name.
  ctx.drawImage(crest, margin, 110, 128, 144);
  ctx.textBaseline = "alphabetic";
  ctx.fillStyle = CHALK;
  ctx.font = "400 76px Anton";
  ctx.fillText("STAR BOY", margin + 160, 210);

  // "MATCHDAY" in spaced gold capitals.
  let y = 440;
  ctx.fillStyle = GOLD;
  ctx.font = "700 40px Barlow";
  ctx.letterSpacing = "10px";
  ctx.fillText("MATCHDAY", margin, y);
  ctx.letterSpacing = "0px";

  // The pitch, as big as it will go.
  ctx.fillStyle = CHALK;
  ctx.font = "400 150px Anton";
  y += 60;
  for (const line of wrap(ctx, game.pitch.name.toUpperCase(), WIDTH - margin * 2).slice(0, 3)) {
    y += 150;
    ctx.fillText(line, margin, y);
  }

  // When: "FRI 9 OCT" on one line, the time in gold on the next.
  const [day, time] = game.kickoff_label.split(", ");
  y += 150;
  ctx.font = "400 104px Anton";
  ctx.fillText(day.toUpperCase(), margin, y);
  y += 128;
  ctx.fillStyle = GOLD;
  ctx.font = "400 128px Anton";
  ctx.fillText(time.toUpperCase(), margin, y);

  if (game.note) {
    y += 76;
    ctx.fillStyle = DIM;
    ctx.font = "600 40px Barlow";
    ctx.fillText(wrap(ctx, game.note, WIDTH - margin * 2)[0], margin, y);
  }

  // Who's in: a chalk rule, then the names in two columns.
  const names = game.players.in.map((player) => player.nickname || player.name.split(" ")[0]);
  y += 90;
  ctx.fillStyle = LINE;
  ctx.fillRect(margin, y, WIDTH - margin * 2, 3);
  y += 70;
  ctx.fillStyle = DIM;
  ctx.font = "700 34px Barlow";
  ctx.letterSpacing = "8px";
  ctx.fillText(`WHO'S IN (${names.length})`, margin, y);
  ctx.letterSpacing = "0px";

  const shown = names.slice(0, 12);
  ctx.fillStyle = CHALK;
  ctx.font = "400 58px Anton";
  shown.forEach((name, index) => {
    const column = index % 2;
    const row = Math.floor(index / 2);
    ctx.fillText(name.toUpperCase().slice(0, 14), margin + column * 460, y + 86 + row * 78);
  });
  if (names.length > shown.length) {
    ctx.fillStyle = GOLD;
    ctx.fillText(`+${names.length - shown.length} MORE`, margin, y + 86 + 6 * 78);
  }

  // The call to action, on the centre circle.
  ctx.textAlign = "center";
  ctx.fillStyle = GOLD;
  ctx.font = "400 84px Anton";
  ctx.fillText("YOU DEY COME?", WIDTH / 2, HEIGHT - 190);
  ctx.fillStyle = DIM;
  ctx.font = "600 34px Barlow";
  ctx.fillText(window.location.host, WIDTH / 2, HEIGHT - 120);
  ctx.textAlign = "left";

  return new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
}

// The "Share poster" button. Tapping it draws the poster and shows it, with
// buttons to share it (WhatsApp Status and the rest) or save it.
export default function PosterButton({ game }) {
  const [poster, setPoster] = useState(null); // { blob, url } once drawn
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Free the picture's memory when the viewer closes.
  useEffect(() => () => poster && URL.revokeObjectURL(poster.url), [poster]);

  async function open() {
    setBusy(true);
    setError("");
    try {
      const blob = await drawPoster(game);
      setPoster({ blob, url: URL.createObjectURL(blob) });
    } catch {
      setError("Star Boy couldn't draw the poster on this phone.");
    }
    setBusy(false);
  }

  const file = poster && new File([poster.blob], "starboy-matchday.png", { type: "image/png" });
  const canShare = file && navigator.canShare?.({ files: [file] });

  async function share() {
    try {
      await navigator.share({ files: [file], title: `Football at ${game.pitch.name}` });
    } catch {
      // They closed the share sheet: nothing to do.
    }
  }

  return (
    <>
      <button className="button secondary" onClick={open} disabled={busy}>
        {busy ? "Drawing…" : "Share poster"}
      </button>
      <ErrorNote error={error} />

      {poster && (
        <div className="lightbox" onClick={() => setPoster(null)} role="dialog" aria-label="Matchday poster">
          <img src={poster.url} alt={`Matchday poster for ${game.pitch.name}, ${game.kickoff_label}`}
               onClick={(event) => event.stopPropagation()} />
          <div className="lightbox-bar" onClick={(event) => event.stopPropagation()}>
            {canShare && <button className="button gold" onClick={share}>Share</button>}
            <a className="button secondary" href={poster.url} download="starboy-matchday.png">Save</a>
            <button className="link-button" onClick={() => setPoster(null)}>Close</button>
          </div>
        </div>
      )}
    </>
  );
}
