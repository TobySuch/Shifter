// Small helpers for talking to Django's JSON endpoints from React islands.

export function getCsrfToken(doc = document) {
  const input = doc.querySelector('input[name="csrfmiddlewaretoken"]');
  if (input?.value) {
    return input.value;
  }

  const match = doc.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

// Flattens a Django form.errors payload ({field: ["msg", ...]}) into a list
// of messages.
export function flattenErrors(errors) {
  if (!errors || typeof errors !== "object") {
    return [];
  }

  return Object.values(errors).flatMap((value) =>
    Array.isArray(value) ? value.map(String) : [String(value)],
  );
}

export class ApiError extends Error {
  constructor(message, { status, errors = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errors = errors;
  }
}

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

export async function apiFetch(url, { method = "GET", body, headers } = {}) {
  const upperMethod = method.toUpperCase();
  const options = {
    method: upperMethod,
    credentials: "same-origin",
    headers: { Accept: "application/json", ...headers },
  };

  if (!SAFE_METHODS.has(upperMethod)) {
    options.headers["X-CSRFToken"] = getCsrfToken();
  }

  if (body instanceof FormData) {
    options.body = body;
  } else if (body !== undefined) {
    options.body = JSON.stringify(body);
    options.headers["Content-Type"] = "application/json";
  }

  const response = await fetch(url, options);

  let data = null;
  try {
    data = await response.json();
  } catch {
    // Non-JSON response (e.g. an HTML error page).
  }

  if (!response.ok) {
    const messages = flattenErrors(data?.errors);
    throw new ApiError(messages[0] || `Request failed (${response.status})`, {
      status: response.status,
      errors: data?.errors ?? null,
    });
  }

  return data;
}
