import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  apiFetch,
  flattenErrors,
  getCsrfToken,
} from "../../assets/js/react/api.js";

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
  document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
});

function jsonResponse(status, data) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
  };
}

describe("getCsrfToken", () => {
  it("prefers the rendered csrf input", () => {
    document.body.innerHTML = `<input name="csrfmiddlewaretoken" value="from-input">`;
    document.cookie = "csrftoken=from-cookie";
    expect(getCsrfToken()).toBe("from-input");
  });

  it("falls back to the csrftoken cookie", () => {
    document.cookie = "csrftoken=from-cookie";
    expect(getCsrfToken()).toBe("from-cookie");
  });

  it("returns null when no token is available", () => {
    expect(getCsrfToken()).toBeNull();
  });
});

describe("flattenErrors", () => {
  it("flattens Django form errors into a message list", () => {
    expect(
      flattenErrors({ a: ["one", "two"], __all__: ["three"], b: "four" }),
    ).toEqual(["one", "two", "three", "four"]);
  });

  it("handles missing errors", () => {
    expect(flattenErrors(undefined)).toEqual([]);
  });
});

describe("apiFetch", () => {
  it("sends the CSRF header and JSON body on unsafe methods", async () => {
    document.body.innerHTML = `<input name="csrfmiddlewaretoken" value="tok">`;
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { ok: 1 }));
    vi.stubGlobal("fetch", fetchMock);

    const data = await apiFetch("/api/x", { method: "post", body: { a: 1 } });

    expect(data).toEqual({ ok: 1 });
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/x");
    expect(options.method).toBe("POST");
    expect(options.headers["X-CSRFToken"]).toBe("tok");
    expect(options.headers["Content-Type"]).toBe("application/json");
    expect(options.body).toBe('{"a":1}');
  });

  it("does not send a CSRF header on GET", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, {}));
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/api/x");

    expect(fetchMock.mock.calls[0][1].headers).not.toHaveProperty(
      "X-CSRFToken",
    );
  });

  it("throws an ApiError carrying Django form errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(jsonResponse(400, { errors: { f: ["Bad value"] } })),
    );

    const error = await apiFetch("/api/x").catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe("Bad value");
    expect(error.status).toBe(400);
    expect(error.errors).toEqual({ f: ["Bad value"] });
  });

  it("throws a generic ApiError for non-JSON failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => {
        throw new SyntaxError("not json");
      },
    }));

    const error = await apiFetch("/api/x").catch((e) => e);

    expect(error.message).toBe("Request failed (500)");
    expect(error.errors).toBeNull();
  });
});
