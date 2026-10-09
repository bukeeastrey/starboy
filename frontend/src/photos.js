// Photos are made small IN THE BROWSER before they are uploaded: a phone
// photo is 3 to 8 MB, and what we send is about 200 KB plus a tiny thumbnail.
// That keeps uploads quick on mobile data and the free server within its limits.

import { api } from "./api.js";

const FULL_SIDE = 1280; // longest side of the gallery version, in pixels
const THUMB_SIDE = 360; // longest side of the thumbnail
const FULL_LIMIT = 600_000; // bytes; if over, we try again at lower quality

// The stock photos used when a pitch has no cover from the crew yet.
// All from Pexels (free licence), stored in public/img/covers.
export const STOCK_COVERS = [1, 2, 3, 4, 5].map((n) => `/img/covers/cover-${n}.jpg`);
export const PHOTO_CREDITS =
  "Kenechukwu Emmanuel, Usman Umar, Praisetoby Praise, B. Aristotle Guweh Jr., Muhammad Shehu, Thato Moiketsi";

// The same pitch always gets the same stock photo; different pitches differ.
export function stockCover(pitchId) {
  let sum = 0;
  for (const char of pitchId) sum += char.charCodeAt(0);
  return STOCK_COVERS[sum % STOCK_COVERS.length];
}

// Load a chosen file as something we can draw (turned the right way up).
async function load(file) {
  if (window.createImageBitmap) {
    try {
      return await createImageBitmap(file, { imageOrientation: "from-image" });
    } catch {
      // Some browsers don't take the option: fall through to the <img> way.
    }
  }
  const image = new Image();
  image.src = URL.createObjectURL(file);
  await image.decode();
  return image;
}

// Draw the picture smaller and save it as a JPEG.
function shrink(picture, maxSide, quality) {
  const scale = Math.min(1, maxSide / Math.max(picture.width, picture.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(picture.width * scale);
  canvas.height = Math.round(picture.height * scale);
  canvas.getContext("2d").drawImage(picture, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", quality));
}

// Make both sizes from a file the player picked.
export async function prepare(file) {
  if (!file.type.startsWith("image/")) throw new Error("Pick a photo.");
  let picture;
  try {
    picture = await load(file);
  } catch {
    throw new Error("Star Boy couldn't open that photo. Try another one.");
  }
  let full = await shrink(picture, FULL_SIDE, 0.8);
  if (full.size > FULL_LIMIT) full = await shrink(picture, FULL_SIDE, 0.6);
  const thumb = await shrink(picture, THUMB_SIDE, 0.72);
  return { full, thumb };
}

// Shrink a photo and send it. `url` is where it goes, e.g. /api/games/<id>/photos
export async function uploadPhoto(url, file) {
  const { full, thumb } = await prepare(file);
  const form = new FormData();
  form.append("full", full, "full.jpg");
  form.append("thumb", thumb, "thumb.jpg");
  return api(url, { method: "POST", body: form });
}
