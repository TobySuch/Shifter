import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  NetworkError,
  readChunks,
  sendChunkWithRetry,
  uploadStream,
} from "../../assets/js/upload/chunked-upload.js";
import { ApiError } from "../../assets/js/react/api.js";
import { streamOf } from "./test-files.js";

async function collect(iterable) {
  const out = [];
  for await (const item of iterable) {
    out.push(Array.from(item));
  }
  return out;
}

describe("readChunks", () => {
  it("re-chunks uneven stream pieces into fixed-size chunks", async () => {
    const stream = streamOf([1, 2, 3], [4], [5, 6, 7, 8, 9]);
    expect(await collect(readChunks(stream, 4))).toEqual([
      [1, 2, 3, 4],
      [5, 6, 7, 8],
      [9],
    ]);
  });

  it("yields nothing for an empty stream", async () => {
    expect(await collect(readChunks(streamOf(), 4))).toEqual([]);
  });

  it("does not emit an empty trailing chunk", async () => {
    expect(await collect(readChunks(streamOf([1, 2], [3, 4]), 2))).toEqual([
      [1, 2],
      [3, 4],
    ]);
  });

  it("cancels the stream when the consumer stops early", async () => {
    const cancel = vi.fn();
    const stream = new ReadableStream({
      pull(controller) {
        controller.enqueue(new Uint8Array([1, 2]));
      },
      cancel,
    });

    for await (const chunk of readChunks(stream, 2)) {
      expect(Array.from(chunk)).toEqual([1, 2]);
      break;
    }

    expect(cancel).toHaveBeenCalled();
  });
});

describe("sendChunkWithRetry", () => {
  const data = new Uint8Array([1, 2, 3]);
  const sleep = vi.fn().mockResolvedValue();
  const base = { url: "/c", data, offset: 10, timeoutMs: 1000, sleep };

  beforeEach(() => sleep.mockClear());

  it("returns the server's received count", async () => {
    const send = vi.fn().mockResolvedValue({ status: 200, data: { received: 13 } });
    expect(await sendChunkWithRetry({ ...base, send })).toBe(13);
    expect(send).toHaveBeenCalledWith(
      expect.objectContaining({ url: "/c", data, offset: 10 }),
    );
  });

  it("retries network errors with backoff", async () => {
    const send = vi
      .fn()
      .mockRejectedValueOnce(new NetworkError("offline"))
      .mockRejectedValueOnce(new NetworkError("offline"))
      .mockResolvedValue({ status: 200, data: { received: 13 } });

    expect(
      await sendChunkWithRetry({ ...base, send, retryDelaysMs: [5, 50, 500] }),
    ).toBe(13);
    expect(sleep.mock.calls).toEqual([[5], [50]]);
  });

  it("retries server errors", async () => {
    const send = vi
      .fn()
      .mockResolvedValueOnce({ status: 502, data: null })
      .mockResolvedValue({ status: 200, data: { received: 13 } });

    expect(await sendChunkWithRetry({ ...base, send })).toBe(13);
  });

  it("gives up after the last retry", async () => {
    const send = vi.fn().mockRejectedValue(new NetworkError("offline"));

    await expect(
      sendChunkWithRetry({ ...base, send, retryDelaysMs: [1, 1] }),
    ).rejects.toBeInstanceOf(NetworkError);
    expect(send).toHaveBeenCalledTimes(3);
  });

  it("treats a conflict showing the chunk already stored as success", async () => {
    const send = vi.fn().mockResolvedValue({
      status: 409,
      data: { errors: { __all__: ["offset"] }, received: 13 },
    });

    expect(await sendChunkWithRetry({ ...base, send })).toBe(13);
  });

  it("fails on a conflict at any other position", async () => {
    const send = vi.fn().mockResolvedValue({
      status: 409,
      data: { errors: { __all__: ["Out of sync"] }, received: 4 },
    });

    await expect(sendChunkWithRetry({ ...base, send })).rejects.toThrow(
      "Out of sync",
    );
    expect(send).toHaveBeenCalledOnce();
  });

  it("does not retry client errors", async () => {
    const send = vi.fn().mockResolvedValue({
      status: 400,
      data: { errors: { __all__: ["Chunk is empty."] } },
    });

    const error = await sendChunkWithRetry({ ...base, send }).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(400);
    expect(error.message).toBe("Chunk is empty.");
    expect(send).toHaveBeenCalledOnce();
  });
});

describe("uploadStream", () => {
  let fetchMock;

  const json = (status, data) => ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
  });

  const session = {
    upload_id: "abc",
    chunk_size: 4,
    chunk_url: "/api/uploads/abc/chunk",
    complete_url: "/api/uploads/abc/complete",
    abort_url: "/api/uploads/abc",
  };

  beforeEach(() => {
    document.body.innerHTML = `<input name="csrfmiddlewaretoken" value="tok">`;
    fetchMock = vi.fn(async (url, options) => {
      if (url === "/api/uploads") return json(201, session);
      if (url === session.complete_url)
        return json(201, { redirect_url: "/files/xyz" });
      if (url === session.abort_url && options.method === "DELETE")
        return { ok: true, status: 204, json: async () => null };
      throw new Error(`unexpected ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => vi.unstubAllGlobals());

  function fakeSender() {
    const calls = [];
    const sendChunkFn = vi.fn(async ({ data, offset, onProgress }) => {
      calls.push({ offset, bytes: Array.from(data) });
      onProgress(data.length);
      return offset + data.length;
    });
    return { calls, sendChunkFn };
  }

  const start = (overrides = {}) =>
    uploadStream({
      initUrl: "/api/uploads",
      filename: "a.bin",
      size: 9,
      stream: streamOf([1, 2, 3, 4, 5], [6, 7, 8, 9]),
      expiryDatetime: "2030-01-01T00:00:00.000Z",
      enableExpiry: true,
      timeoutMs: 1000,
      ...overrides,
    });

  it("initialises, sends every chunk in order and completes", async () => {
    const { calls, sendChunkFn } = fakeSender();
    const onProgress = vi.fn();

    const redirect = await start({ sendChunkFn, onProgress });

    expect(redirect).toBe("/files/xyz");
    const [initUrl, initOptions] = fetchMock.mock.calls[0];
    expect(initUrl).toBe("/api/uploads");
    expect(JSON.parse(initOptions.body)).toEqual({
      filename: "a.bin",
      size: 9,
      enable_expiry: true,
      expiry_datetime: "2030-01-01T00:00:00.000Z",
    });
    expect(calls).toEqual([
      { offset: 0, bytes: [1, 2, 3, 4] },
      { offset: 4, bytes: [5, 6, 7, 8] },
      { offset: 8, bytes: [9] },
    ]);
    expect(fetchMock.mock.calls.at(-1)[0]).toBe(session.complete_url);
    expect(onProgress).toHaveBeenLastCalledWith(9, 9);
  });

  it("surfaces init validation errors without sending chunks", async () => {
    fetchMock.mockImplementationOnce(async () =>
      json(400, { errors: { size: ["You can't upload a file larger than 1KB"] } }),
    );
    const { sendChunkFn } = fakeSender();

    const error = await start({ sendChunkFn }).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.errors).toEqual({
      size: ["You can't upload a file larger than 1KB"],
    });
    expect(sendChunkFn).not.toHaveBeenCalled();
  });

  it("aborts the server session when a chunk fails", async () => {
    const sendChunkFn = vi.fn().mockRejectedValue(new NetworkError("offline"));

    await expect(start({ sendChunkFn })).rejects.toBeInstanceOf(NetworkError);

    await vi.waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        session.abort_url,
        expect.objectContaining({ method: "DELETE" }),
      ),
    );
    expect(fetchMock).not.toHaveBeenCalledWith(
      session.complete_url,
      expect.anything(),
    );
  });

  it("fails and aborts if the stream is shorter than declared", async () => {
    const { sendChunkFn } = fakeSender();

    await expect(start({ size: 20, sendChunkFn })).rejects.toThrow(
      /Expected 20 bytes but read 9/,
    );
    await vi.waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        session.abort_url,
        expect.objectContaining({ method: "DELETE" }),
      ),
    );
  });
});
