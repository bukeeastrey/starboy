// A tiny router, so we don't need an extra library.
// It uses the browser's History API: the address bar changes, the page doesn't reload.

import { useSyncExternalStore } from "react";

const listeners = new Set();

function subscribe(listener) {
  listeners.add(listener);
  window.addEventListener("popstate", listener); // the Back/Forward buttons
  return () => {
    listeners.delete(listener);
    window.removeEventListener("popstate", listener);
  };
}

// Go to another screen, e.g. navigate("/pitch/123").
export function navigate(path, { replace = false } = {}) {
  if (replace) window.history.replaceState(null, "", path);
  else window.history.pushState(null, "", path);
  window.scrollTo(0, 0);
  listeners.forEach((listener) => listener());
}

// The current path ("/pitch/123"). The component re-renders when it changes.
export function usePath() {
  return useSyncExternalStore(subscribe, () => window.location.pathname);
}

// Does "/pitch/:id" match "/pitch/123"? Returns { id: "123" }, or null.
export function matchRoute(pattern, path) {
  const patternParts = pattern.split("/").filter(Boolean);
  const pathParts = path.split("/").filter(Boolean);
  if (patternParts.length !== pathParts.length) return null;

  const params = {};
  for (let i = 0; i < patternParts.length; i++) {
    if (patternParts[i].startsWith(":")) {
      params[patternParts[i].slice(1)] = decodeURIComponent(pathParts[i]);
    } else if (patternParts[i] !== pathParts[i]) {
      return null;
    }
  }
  return params;
}

// A link that changes the screen without reloading the page.
export function Link({ to, className, children }) {
  function onClick(event) {
    // Let Ctrl/Cmd-click open a new tab as usual.
    if (event.ctrlKey || event.metaKey || event.shiftKey) return;
    event.preventDefault();
    navigate(to);
  }
  return (
    <a href={to} className={className} onClick={onClick}>
      {children}
    </a>
  );
}
