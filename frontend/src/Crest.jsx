// The Star Boy badge and a few small line icons, drawn as SVG so they stay
// crisp at any size. (The same crest is in public/crest.svg for the favicon.)

export function Crest({ size = 40 }) {
  return (
    <svg
      className="crest" viewBox="0 0 64 72" width={size} height={size * 1.125}
      role="img" aria-label="Star Boy"
    >
      <path
        d="M32 3 58 11v25c0 15-10.5 25.5-26 32C16.5 61.5 6 51 6 36V11z"
        fill="#0c1f16" stroke="#f5c518" strokeWidth="3" strokeLinejoin="round"
      />
      <path
        d="M32 9.5 52.5 15.6V36c0 11.7-8 20.3-20.5 26C19.5 56.3 11.5 47.7 11.5 36V15.6z"
        fill="none" stroke="#f1f4ee" strokeWidth=".9" strokeOpacity=".45" strokeLinejoin="round"
      />
      <polygon
        points="32,17 35.14,26.67 45.32,26.67 37.09,32.65 40.23,42.33 32,36.35 23.77,42.33 26.91,32.65 18.68,26.67 28.86,26.67"
        fill="#f5c518"
      />
      <path
        d="M19 49.5h26M26 49.5a6 6 0 0 0 12 0"
        fill="none" stroke="#f1f4ee" strokeWidth="1.1" strokeOpacity=".7" strokeLinecap="round"
      />
    </svg>
  );
}

// The crest next to the name, as in a club's letterhead.
export function Wordmark({ size = 34 }) {
  return (
    <span className="wordmark">
      <Crest size={size} />
      <span>Star Boy</span>
    </span>
  );
}

export function MicIcon() {
  return (
    <svg viewBox="0 0 24 24" width="56" height="56" fill="none" stroke="currentColor"
         strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.500V21M8.500 21h7" />
    </svg>
  );
}

export function StopIcon() {
  return (
    <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor" aria-hidden="true">
      <rect x="6.500" y="6.500" width="11" height="11" rx="1.500" />
    </svg>
  );
}

// A small medal for the man of the match.
export function MedalIcon({ size = 28 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor"
         strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M8 3 12 10 16 3" />
      <circle cx="12" cy="15" r="5.500" />
      <path d="M12 12.600 12.800 14.300 14.600 14.500 13.300 15.700 13.600 17.500 12 16.600 10.400 17.500 10.700 15.700 9.400 14.500 11.200 14.300z"
            fill="currentColor" stroke="none" />
    </svg>
  );
}
