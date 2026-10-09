// Star Boy as a Telegram "Mini App": the website opened inside Telegram.
//
// When Telegram opens the page it adds launch data to the address, after the
// "#". We send that to the backend, which checks Telegram really made it and
// signs the player in. No phone number, no PIN.

import { api } from "./api.js";

// The launch data, or "" when the page was opened in a normal browser.
export function telegramInitData() {
  const hash = new URLSearchParams(window.location.hash.slice(1));
  return hash.get("tgWebAppData") || window.Telegram?.WebApp?.initData || "";
}

// Telegram's own small script: tells Telegram the page is ready and asks for
// the full height. Loaded only inside Telegram, so normal visitors skip it.
function loadTelegramScript() {
  if (document.getElementById("telegram-web-app")) return;
  const script = document.createElement("script");
  script.id = "telegram-web-app";
  script.src = "https://telegram.org/js/telegram-web-app.js";
  script.onload = () => {
    window.Telegram?.WebApp?.ready();
    window.Telegram?.WebApp?.expand();
  };
  document.head.appendChild(script);
}

// Sign in with the launch data. Resolves to true if that worked.
export async function signInFromTelegram() {
  const initData = telegramInitData();
  if (!initData) return false;
  loadTelegramScript();
  try {
    await api("/api/auth/telegram", { method: "POST", body: { init_data: initData } });
    return true;
  } catch {
    return false; // no account yet (they should send /start to the bot), or old data
  }
}
