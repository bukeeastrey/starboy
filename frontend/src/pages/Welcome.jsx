import { Link } from "../router.jsx";

// The first screen for someone who is not signed in.
// "invited" is true when they opened a game link a friend sent them.
export default function Welcome({ invited }) {
  return (
    <div className="welcome">
      <div className="logo">⭐</div>
      <h1>Star Boy</h1>
      <p className="tagline">Comot for room. Come play ball. ⚽</p>
      {invited && (
        <p className="card">
          Your people dey call you for football! Join Star Boy to answer the invite.
        </p>
      )}
      <Link to="/signup" className="button big">Join Star Boy</Link>
      <Link to="/signin" className="button big secondary">I already have an account</Link>
    </div>
  );
}
