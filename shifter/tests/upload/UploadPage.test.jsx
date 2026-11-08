import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { toDateTimeLocalValue } from "../../assets/js/dates.js";
import UploadPage from "../../assets/js/upload/UploadPage.jsx";
import { STAY_ON_PAGE_MESSAGE } from "../../assets/js/upload/upload-logic.js";
import { createFakePond } from "./fake-pond.js";

const HOUR = 60 * 60 * 1000;

function buildProps(overrides = {}) {
  const now = Date.now();
  return {
    uploadUrl: "/",
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

function renderUploadPage(overrides = {}) {
  const { pond, factory } = createFakePond();
  const navigate = vi.fn();
  const props = buildProps(overrides);
  const utils = render(
    <UploadPage {...props} createPond={factory} navigate={navigate} />,
  );
  return { ...utils, pond, factory, navigate, props };
}

const uploadButton = () => screen.getByRole("button", { name: "Upload" });
const txt = (name, content = "x") => new File([content], name);

beforeEach(() => {
  document.body.innerHTML = `<input name="csrfmiddlewaretoken" value="csrf-tok">`;
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("UploadPage", () => {
  it("configures FilePond from the island props", () => {
    const { factory, pond } = renderUploadPage({ uploadTimeout: 900 });

    expect(factory).toHaveBeenCalledOnce();
    const options = factory.mock.calls[0][0];
    expect(options.name).toBe("file_content");
    expect(options.maxFileSize).toBe("5MB");
    expect(options.allowMultiple).toBe(true);
    expect(options.instantUpload).toBe(false);
    expect(options.server.process.url).toBe("/");
    expect(options.server.process.timeout).toBe(900_000);
    expect(options.server.process.headers["X-CSRFToken"]).toBe("csrf-tok");
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

  it("uploads a single file and shows the stay-on-page notice", async () => {
    const user = userEvent.setup();
    const { pond } = renderUploadPage();
    act(() => pond.simulateAdd(txt("a.txt")));

    await user.click(uploadButton());

    expect(pond.processFiles).toHaveBeenCalledOnce();
    expect(pond.addFile).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(STAY_ON_PAGE_MESSAGE);
    expect(uploadButton()).toBeDisabled();
  });

  it("zips multiple files using the chosen zip name", async () => {
    const user = userEvent.setup();
    const { pond } = renderUploadPage();
    act(() => {
      pond.simulateAdd(txt("a.txt"));
      pond.simulateAdd(txt("b.txt"));
    });

    const zipInput = screen.getByLabelText("Zip File Name:");
    expect(zipInput).toHaveValue("combined");
    await user.clear(zipInput);
    await user.type(zipInput, "holiday");
    await user.click(uploadButton());

    await waitFor(() => expect(pond.processFiles).toHaveBeenCalledOnce());
    expect(pond.removeFiles).toHaveBeenCalledOnce();
    expect(pond.addFile.mock.calls[0][0].name).toBe("holiday.zip");
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

  it("redirects to the file details page on success", () => {
    const { pond, navigate } = renderUploadPage();

    pond.options.server.process.onload('{"redirect_url": "/files/abc123"}');

    expect(navigate).toHaveBeenCalledWith("/files/abc123");
  });

  it("shows server errors and allows retrying", async () => {
    const user = userEvent.setup();
    const { pond } = renderUploadPage();
    act(() => pond.simulateAdd(txt("a.txt")));
    await user.click(uploadButton());
    expect(uploadButton()).toBeDisabled();

    act(() =>
      pond.options.server.process.onerror(
        JSON.stringify({
          errors: { file_content: ["You can't upload a file larger than 5MB"] },
        }),
      ),
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "You can't upload a file larger than 5MB",
    );
    expect(uploadButton()).toBeEnabled();
  });

  it("handles FilePond's processFiles rejection on server errors", async () => {
    const user = userEvent.setup();
    const { pond } = renderUploadPage();
    // FilePond rejects processFiles() when the server returns an error; the
    // message itself is shown via the onerror callback. A plain function is
    // used because vi.fn() marks returned promises as handled.
    let calls = 0;
    pond.processFiles = () => {
      calls += 1;
      return Promise.reject({ error: { code: 400 }, file: {} });
    };
    act(() => pond.simulateAdd(txt("a.txt")));

    await user.click(uploadButton());

    // An unhandled rejection here would fail the Vitest run.
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(calls).toBe(1);
  });

  it("does not render server error messages as HTML", () => {
    const { pond } = renderUploadPage();

    act(() =>
      pond.options.server.process.onerror(
        JSON.stringify({ errors: { __all__: ["<img src=x onerror=alert(1)>"] } }),
      ),
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "<img src=x onerror=alert(1)>",
    );
    expect(screen.getByRole("alert").querySelector("img")).toBeNull();
  });

  describe("expiry", () => {
    it("always sends expiry when optional expiry is disabled", () => {
      const props = buildProps();
      const { pond } = renderUploadPage(props);

      expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
      const input = screen.getByLabelText("Expiry:");
      expect(input).toHaveValue(
        toDateTimeLocalValue(new Date(props.expiry.initial)),
      );

      const formData = pond.options.server.process.ondata(new FormData());
      expect(formData.get("enable_expiry")).toBe("on");
      expect(formData.get("expiry_datetime")).toBe(
        new Date(input.value).toISOString(),
      );
      expect(formData.get("csrfmiddlewaretoken")).toBe("csrf-tok");
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
      const { pond } = renderUploadPage({ allowOptionalExpiry: true });

      const checkbox = screen.getByRole("checkbox", {
        name: "Set file expiry:",
      });
      expect(checkbox).not.toBeChecked();
      expect(screen.queryByLabelText("Expiry:")).not.toBeInTheDocument();

      let formData = pond.options.server.process.ondata(new FormData());
      expect(formData.get("enable_expiry")).toBe("");
      expect(formData.has("expiry_datetime")).toBe(false);

      await user.click(checkbox);

      expect(screen.getByLabelText("Expiry:")).toBeInTheDocument();
      formData = pond.options.server.process.ondata(new FormData());
      expect(formData.get("enable_expiry")).toBe("on");
      expect(formData.has("expiry_datetime")).toBe(true);
    });

    it("clears an expiry error once the user unchecks expiry", async () => {
      const user = userEvent.setup();
      const { pond } = renderUploadPage({ allowOptionalExpiry: true });
      await user.click(screen.getByRole("checkbox"));

      act(() =>
        pond.options.server.process.onerror(
          JSON.stringify({ errors: { expiry_datetime: ["In the past"] } }),
        ),
      );
      expect(screen.getByRole("alert")).toHaveTextContent("In the past");

      await user.click(screen.getByRole("checkbox"));

      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("clears an expiry error once a valid expiry is entered", () => {
      const { pond } = renderUploadPage();
      act(() =>
        pond.options.server.process.onerror(
          JSON.stringify({ errors: { expiry_datetime: ["In the past"] } }),
        ),
      );
      expect(screen.getByRole("alert")).toBeInTheDocument();

      const input = screen.getByLabelText("Expiry:");
      const valid = toDateTimeLocalValue(new Date(Date.now() + 2 * HOUR));
      // datetime-local can't be typed into reliably under jsdom; set the
      // value through React's change handler instead.
      fireEvent.change(input, { target: { value: valid } });

      expect(input).toHaveValue(valid);
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("keeps a file error when the expiry changes", () => {
      const { pond } = renderUploadPage();
      act(() =>
        pond.options.server.process.onerror(
          JSON.stringify({ errors: { file_content: ["Too big"] } }),
        ),
      );

      fireEvent.change(screen.getByLabelText("Expiry:"), {
        target: {
          value: toDateTimeLocalValue(new Date(Date.now() + 2 * HOUR)),
        },
      });

      expect(screen.getByRole("alert")).toHaveTextContent("Too big");
    });
  });
});
