// Client for the chunked upload API (shifter_files/api.py).

import { ApiError, apiFetch, flattenErrors, getCsrfToken } from "../react/api.js";

// Re-chunks a byte stream into Uint8Arrays of exactly chunkSize bytes (the
// last may be shorter). Only one chunk is buffered at a time, and the next
// one isn't read until the consumer asks for it.
export async function* readChunks(stream, chunkSize) {
  const reader = stream.getReader();
  let buffer = new Uint8Array(chunkSize);
  let filled = 0;
  let finished = false;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        finished = true;
        break;
      }

      let consumed = 0;
      while (consumed < value.length) {
        const take = Math.min(chunkSize - filled, value.length - consumed);
        buffer.set(value.subarray(consumed, consumed + take), filled);
        filled += take;
        consumed += take;

        if (filled === chunkSize) {
          yield buffer;
          buffer = new Uint8Array(chunkSize);
          filled = 0;
        }
      }
    }

    if (filled > 0) {
      yield buffer.subarray(0, filled);
    }
  } finally {
    if (!finished) {
      await reader.cancel().catch(() => {});
    }
    reader.releaseLock();
  }
}

export class NetworkError extends Error {
  constructor(message) {
    super(message);
    this.name = "NetworkError";
  }
}

// Sends one chunk with XMLHttpRequest, which (unlike fetch) reports upload
// progress. Resolves with { status, data } for any HTTP response and rejects
// with NetworkError if the request never completed.
export function sendChunk({ url, data, offset, timeoutMs, onProgress }) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("Content-Type", "application/octet-stream");
    xhr.setRequestHeader("X-Upload-Offset", String(offset));
    xhr.setRequestHeader("X-CSRFToken", getCsrfToken());
    xhr.setRequestHeader("Accept", "application/json");
    xhr.timeout = timeoutMs;

    xhr.upload.onprogress = (event) => onProgress?.(event.loaded);
    xhr.onload = () => {
      let body = null;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        // Non-JSON response (e.g. a proxy error page).
      }
      resolve({ status: xhr.status, data: body });
    };
    xhr.onerror = () => reject(new NetworkError("Network error"));
    xhr.ontimeout = () => reject(new NetworkError("Upload timed out"));

    xhr.send(data);
  });
}

const defaultSleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export async function sendChunkWithRetry({
  url,
  data,
  offset,
  timeoutMs,
  onProgress,
  send = sendChunk,
  sleep = defaultSleep,
  retryDelaysMs = [1000, 3000, 10000],
}) {
  const expected = offset + data.length;

  for (let attempt = 0; ; attempt++) {
    let response;
    try {
      response = await send({ url, data, offset, timeoutMs, onProgress });
    } catch (error) {
      if (!(error instanceof NetworkError) || attempt >= retryDelaysMs.length) {
        throw error;
      }
      await sleep(retryDelaysMs[attempt]);
      continue;
    }

    const { status, data: body } = response;

    if (status >= 200 && status < 300) {
      return body.received;
    }

    // A previous attempt reached the server but its response was lost.
    if (status === 409 && body?.received === expected) {
      return expected;
    }

    if (status >= 500 && attempt < retryDelaysMs.length) {
      await sleep(retryDelaysMs[attempt]);
      continue;
    }

    const messages = flattenErrors(body?.errors);
    throw new ApiError(messages[0] || `Upload failed (${status})`, {
      status,
      errors: body?.errors ?? null,
    });
  }
}

// Uploads a byte stream through the chunked upload API and returns the
// redirect URL of the new file. The server-side session is discarded if
// anything goes wrong.
export async function uploadStream({
  initUrl,
  filename,
  size,
  stream,
  expiryDatetime,
  enableExpiry,
  timeoutMs,
  onProgress,
  sendChunkFn = sendChunkWithRetry,
}) {
  let session;
  try {
    session = await apiFetch(initUrl, {
      method: "POST",
      body: {
        filename,
        size,
        enable_expiry: enableExpiry,
        expiry_datetime: expiryDatetime,
      },
    });
  } catch (error) {
    await stream.cancel().catch(() => {});
    throw error;
  }

  try {
    let offset = 0;
    onProgress?.(0, size);

    for await (const chunk of readChunks(stream, session.chunk_size)) {
      const chunkStart = offset;
      offset = await sendChunkFn({
        url: session.chunk_url,
        data: chunk,
        offset: chunkStart,
        timeoutMs,
        onProgress: (loaded) =>
          onProgress?.(Math.min(chunkStart + loaded, size), size),
      });
      onProgress?.(offset, size);
    }

    if (offset !== size) {
      throw new Error(
        `Expected ${size} bytes but read ${offset}; did the file change?`,
      );
    }

    const result = await apiFetch(session.complete_url, { method: "POST" });
    return result.redirect_url;
  } catch (error) {
    apiFetch(session.abort_url, { method: "DELETE" }).catch(() => {});
    throw error;
  }
}
