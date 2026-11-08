import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import JSZip from "jszip";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { toDateTimeLocalValue } from "../../assets/js/dates.js";
import { ApiError } from "../../assets/js/react/api.js";
import UploadPage from "../../assets/js/upload/UploadPage.jsx";
import { STAY_ON_PAGE_MESSAGE } from "../../assets/js/upload/upload-logic.js";
import { createFakePond } from "./fake-pond.js";
import { readAll, streamableFile } from "./test-files.js";

const HOUR = 60 * 60 * 1000;

function buildProps(overrides = {}) {
  const now = Date.now();
  return {
    initUrl: "/api/uploads",
    fileFieldName: "file_content",
    maxFileSize: "5MB",
    uploadTimeout: 300,
    allowOptionalExpiry: false,
    expiry: {
      initial: new Date(now + 24 * HOUR).toISOString(),
      min: new Date(now).toISOString(),
      max: new Date(now + 48 * HOUR).toISOString(),
    },
    ...overrides,
  };
}

// An upload function whose outcome each test controls.
function controllableUpload() {
  let resolve;
  let reject;
  const upload = vi.fn(
    () =>
      new Promise((res, rej) => {
        resolve = res;
        reject = rej;
      }),
  );
  return {
    upload,
    resolve: (value) => act(async () => resolve(value)),
    reject: (error) => act(async () => reject(error)),
    args: () => upload.mock.calls[0][0],
  };
}

function renderUploadPage(overrides = {}) {
  const { pond, factory } = createFakePond();
  const navigate = vi.fn();
  const uploadControl = controllableUpload();
  const props = buildProps(overrides);
  const utils = render(
    <UploadPage
      {...props}
      createPond={factory}
      upload={uploadControl.upload}
      navigate={navigate}
    />,
  );
  return { ...utils, pond, factory, navigate, props, ...uploadControl };
}

const uploadButton = () => screen.getByRole("button", { name: "Upload" });
const txt = (name, content = "x") => streamableFile(content, name);

beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("UploadPage", () => {
  it("configures FilePond as a picker only", () => {
    const { factory, pond } = renderUploadPage();

    expect(factory).toHaveBeenCalledOnce();
    const options = factory.mock.calls[0][0];
    expect(options.name).toBe("file_content");
    expect(options.maxFileSize).toBe("5MB");
    expect(options.allowMultiple).toBe(true);
    expect(options.instantUpload).toBe(false);
    expect(options.server).toBeUndefined();
    expect(screen.getByTestId("filepond-host")).toContainElement(
      pond.element,
    );
  });

  it("destroys FilePond on unmount", () => {
    const { pond, unmount } = renderUploadPage();
    unmount();
    expect(pond.destroy).toHaveBeenCalledOnce();
  });

  it("disables upload until a file is added", () => {
    const { pond } = renderUploadPage();
    expect(uploadButton()).toBeDisabled();

    act(() => pond.simulateAdd(txt("a.txt")));

    expect(uploadButton()).toBeEnabled();
    expect(screen.queryByLabelText("Zip File Name:")).not.toBeInTheDocument();
  });

  it("uploads a single file through the chunked uploader", async () => {
    const user = userEvent.setup();
    const { pond, upload, args } = renderUploadPage({ uploadTimeout: 900 });
    act(() => pond.simulateAdd(txt("a.txt", "hello")));

    await user.click(uploadButton());

    expect(upload).toHaveBeenCalledOnce();
    const call = args();
    expect(call.initUrl).toBe("/api/uploads");
    expect(call.filename).toBe("a.txt");
    expect(call.size).toBe(5);
    expect(call.timeoutMs).toBe(900_000);
    expect(new TextDecoder().decode(await readAll(call.stream))).toBe("hello");
    expect(screen.getByRole("alert")).toHaveTextContent(STAY_ON_PAGE_MESSAGE);
    expect(uploadButton()).toBeDisabled();
    expect(pond.setOptions).toHaveBeenCalledWith({ disabled: true });
  });

  it("streams multiple files as a zip with the chosen name", async () => {
    const user = userEvent.setup();
    const { pond, args } = renderUploadPage();
    act(() => {
      pond.simulateAdd(txt("a.txt", "alpha"));
      pond.simulateAdd(txt("b.txt", "bravo"));
    });

    const zipInput = screen.getByLabelText("Zip File Name:");
    expect(zipInput).toHaveValue("combined");
    await user.clear(zipInput);
    await user.type(zipInput, "holiday");
    await user.click(uploadButton());

    const call = args();
    expect(call.filename).toBe("holiday.zip");
    const bytes = await readAll(call.stream);
    expect(bytes.length).toBe(call.size);
    const zip = await JSZip.loadAsync(bytes);
    expect(Object.keys(zip.files).sort()).toEqual(["a.txt", "b.txt"]);
    // The queued files themselves are left alone.
    expect(pond.removeFiles).not.toHaveBeenCalled();
    expect(pond.addFile).not.toHaveBeenCalled();
  });

  it("shows upload progress", async () => {
    const user = userEvent.setup();
    const { pond, args } = renderUploadPage();
    act(() => pond.simulateAdd(txt("a.txt", "x".repeat(2048))));
    await user.click(uploadButton());

    act(() => args().onProgress(1024, 2048));

    const bar = screen.getByRole("progressbar", { name: "Upload progress" });
    expect(bar).toHaveAttribute("aria-valuenow", "50");
    expect(screen.getByText("50% · 1.0 KB of 2.0 KB")).toBeInTheDocument();
  });

  it("redirects to the file details page on success", async () => {
    const user = userEvent.setup();
    const { pond, navigate, resolve } = renderUploadPage();
    act(() => pond.simulateAdd(txt("a.txt")));
    await user.click(uploadButton());

    await resolve("/files/abc123");

    expect(navigate).toHaveBeenCalledWith("/files/abc123");
  });

  it("shows validation errors from the server and allows retrying", async () => {
    const user = userEvent.setup();
    const { pond, upload, reject } = renderUploadPage();
    act(() => pond.simulateAdd(txt("a.txt")));
    await user.click(uploadButton());

    await reject(
      new ApiError("too big", {
        status: 400,
        errors: { size: ["You can't upload a file larger than 5MB"] },
      }),
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "You can't upload a file larger than 5MB",
    );
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
    expect(uploadButton()).toBeEnabled();
    expect(pond.setOptions).toHaveBeenLastCalledWith({ disabled: false });

    await user.click(uploadButton());
    expect(upload).toHaveBeenCalledTimes(2);
  });

  it("shows network failures", async () => {
    const user = userEvent.setup();
    const { pond, reject } = renderUploadPage();
    act(() => pond.simulateAdd(txt("a.txt")));
    await user.click(uploadButton());

    await reject(new Error("Upload timed out"));

    expect(screen.getByRole("alert")).toHaveTextContent("Upload timed out");
  });

  it("shows add-file validation errors and blocks upload", () => {
    const { pond } = renderUploadPage();

    act(() =>
      pond.simulateAdd(txt("big.bin"), {
        main: "File is too large",
        sub: "Maximum file size is 5MB",
      }),
    );

    expect(screen.getByRole("alert")).toHaveTextContent("File is too large");
    expect(uploadButton()).toBeDisabled();

    act(() => pond.simulateRemoveAll());

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("does not render server error messages as HTML", async () => {
    const user = userEvent.setup();
    const { pond, reject } = renderUploadPage();
    act(() => pond.simulateAdd(txt("a.txt")));
    await user.click(uploadButton());

    await reject(
      new ApiError("x", {
        status: 400,
        errors: { __all__: ["<img src=x onerror=alert(1)>"] },
      }),
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "<img src=x onerror=alert(1)>",
    );
    expect(screen.getByRole("alert").querySelector("img")).toBeNull();
  });

  describe("expiry", () => {
    it("always sends expiry when optional expiry is disabled", async () => {
      const user = userEvent.setup();
      const props = buildProps();
      const { pond, args } = renderUploadPage(props);

      expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
      const input = screen.getByLabelText("Expiry:");
      expect(input).toHaveValue(
        toDateTimeLocalValue(new Date(props.expiry.initial)),
      );

      act(() => pond.simulateAdd(txt("a.txt")));
      await user.click(uploadButton());

      expect(args().enableExpiry).toBe(true);
      expect(args().expiryDatetime).toBe(new Date(input.value).toISOString());
    });

    it("sets min and max bounds on the input", () => {
      const props = buildProps();
      renderUploadPage(props);

      const input = screen.getByLabelText("Expiry:");
      expect(input).toHaveAttribute(
        "min",
        toDateTimeLocalValue(new Date(props.expiry.min)),
      );
      expect(input).toHaveAttribute(
        "max",
        toDateTimeLocalValue(new Date(props.expiry.max)),
      );
    });

    it("omits max when the server sends none", () => {
      const props = buildProps();
      renderUploadPage({ expiry: { ...props.expiry, max: null } });

      expect(screen.getByLabelText("Expiry:")).not.toHaveAttribute("max");
    });

    it("lets the user opt out when optional expiry is allowed", async () => {
      const user = userEvent.setup();
      const { pond, args, upload } = renderUploadPage({
        allowOptionalExpiry: true,
      });
      act(() => pond.simulateAdd(txt("a.txt")));

      const checkbox = screen.getByRole("checkbox", {
        name: "Set file expiry:",
      });
      expect(checkbox).not.toBeChecked();
      expect(screen.queryByLabelText("Expiry:")).not.toBeInTheDocument();

      await user.click(uploadButton());

      expect(upload).toHaveBeenCalledOnce();
      expect(args().enableExpiry).toBe(false);
      expect(args().expiryDatetime).toBeNull();
    });

    it("sends expiry once the user opts in", async () => {
      const user = userEvent.setup();
      const { pond, args } = renderUploadPage({ allowOptionalExpiry: true });
      act(() => pond.simulateAdd(txt("a.txt")));

      await user.click(screen.getByRole("checkbox"));
      expect(screen.getByLabelText("Expiry:")).toBeInTheDocument();
      await user.click(uploadButton());

      expect(args().enableExpiry).toBe(true);
      expect(args().expiryDatetime).toEqual(expect.any(String));
    });

    async function failWithExpiryError(user, pond, reject) {
      act(() => pond.simulateAdd(txt("a.txt")));
      await user.click(uploadButton());
      await reject(
        new ApiError("past", {
          status: 400,
          errors: { expiry_datetime: ["In the past"] },
        }),
      );
      expect(screen.getByRole("alert")).toHaveTextContent("In the past");
    }

    it("clears an expiry error once the user unchecks expiry", async () => {
      const user = userEvent.setup();
      const { pond, reject } = renderUploadPage({ allowOptionalExpiry: true });
      await user.click(screen.getByRole("checkbox"));
      await failWithExpiryError(user, pond, reject);

      await user.click(screen.getByRole("checkbox"));

      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("clears an expiry error once a valid expiry is entered", async () => {
      const user = userEvent.setup();
      const { pond, reject } = renderUploadPage();
      await failWithExpiryError(user, pond, reject);

      const input = screen.getByLabelText("Expiry:");
      const valid = toDateTimeLocalValue(new Date(Date.now() + 2 * HOUR));
      // datetime-local can't be typed into reliably under jsdom.
      fireEvent.change(input, { target: { value: valid } });

      expect(input).toHaveValue(valid);
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("keeps a file error when the expiry changes", async () => {
      const user = userEvent.setup();
      const { pond, reject } = renderUploadPage();
      act(() => pond.simulateAdd(txt("a.txt")));
      await user.click(uploadButton());
      await reject(
        new ApiError("big", {
          status: 400,
          errors: { size: ["Too big"] },
        }),
      );

      fireEvent.change(screen.getByLabelText("Expiry:"), {
        target: {
          value: toDateTimeLocalValue(new Date(Date.now() + 2 * HOUR)),
        },
      });

      await waitFor(() =>
        expect(screen.getByRole("alert")).toHaveTextContent("Too big"),
      );
    });
  });
});
