import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  cleanupExpiredFiles,
  pruneTaskResults,
} from "../assets/js/site-settings.js";

function respondWith(json) {
  return vi.fn().mockResolvedValue({ json: () => Promise.resolve(json) });
}

describe("site settings admin actions", () => {
  let store;
  let button;

  beforeEach(() => {
    document.cookie = "csrftoken=test-token";
    store = { setExpiredInfo: vi.fn() };
    window.Alpine = { store: () => store };
    button = document.createElement("button");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete window.Alpine;
  });

  it("prunes task results and reports how many were deleted", async () => {
    const fetchMock = respondWith({ success: true, num_results_deleted: 3 });
    vi.stubGlobal("fetch", fetchMock);

    await pruneTaskResults.call(button);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/prune-task-results",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-CSRFToken": "test-token" }),
      }),
    );
    expect(store.setExpiredInfo).toHaveBeenCalledWith(
      "Deleted 3 finished task records.",
    );
    expect(button.disabled).toBe(false);
  });

  it("uses the singular for one task record", async () => {
    vi.stubGlobal(
      "fetch",
      respondWith({ success: true, num_results_deleted: 1 }),
    );

    await pruneTaskResults.call(button);

    expect(store.setExpiredInfo).toHaveBeenCalledWith(
      "Deleted 1 finished task record.",
    );
  });

  it("disables the button while the request is in flight", async () => {
    let resolve;
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise((r) => {
            resolve = r;
          }),
      ),
    );

    const pending = pruneTaskResults.call(button);
    expect(button.disabled).toBe(true);

    resolve({ json: () => Promise.resolve({ success: true }) });
    await pending;
    expect(button.disabled).toBe(false);
  });

  it("still cleans up expired files", async () => {
    const fetchMock = respondWith({ success: true, num_files_deleted: 2 });
    vi.stubGlobal("fetch", fetchMock);

    await cleanupExpiredFiles.call(button);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/cleanup-files",
      expect.objectContaining({ method: "POST" }),
    );
    expect(store.setExpiredInfo).toHaveBeenCalledWith(
      "Successfully deleted 2 files.",
    );
  });
});
