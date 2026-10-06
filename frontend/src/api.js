// Every call to the backend goes through here.

// Turn the backend's error answer into one friendly sentence.
function errorMessage(data, status) {
  if (data && typeof data.detail === "string") return data.detail;
  if (status === 422) return "Please check what you typed.";
  if (status >= 500) return "Star Boy's server had a problem. Try again.";
  return `Something went wrong (${status}).`;
}

// Talk to the backend and get JSON back.
//   api("/api/pitches")                               -> GET
//   api("/api/pitches", { method: "POST", body: {} }) -> POST with JSON
//   body can also be a FormData (used to upload a voice note).
export async function api(path, { method = "GET", body } = {}) {
  const options = { method, headers: {} };
  if (body instanceof FormData) {
    options.body = body; // the browser sets the right Content-Type itself
  } else if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new Error("Can't reach Star Boy. Check your internet.");
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(errorMessage(data, response.status));
    error.status = response.status;
    throw error;
  }
  return data;
}
