// Every call to the backend goes through here.

// GET a JSON answer from the backend, e.g. api("/api/health").
export async function api(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json();
}
