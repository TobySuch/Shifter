import { useEffect, useRef, useState } from "react";

import { toDateTimeLocalValue } from "../dates.js";
import { getCsrfToken } from "../react/api.js";
import AlertBox from "./AlertBox.jsx";
import ExpiryPicker from "./ExpiryPicker.jsx";
import { createFilePond } from "./pond.js";
import {
  appendUploadFields,
  combineFiles,
  DEFAULT_ZIP_NAME,
  describeAddFileError,
  GENERIC_UPLOAD_ERROR,
  parseUploadError,
  parseUploadResponse,
  STAY_ON_PAGE_MESSAGE,
} from "./upload-logic.js";

function navigateTo(url) {
  window.location.assign(url);
}

export default function UploadPage({
  uploadUrl,
  fileFieldName,
  maxFileSize,
  uploadTimeout,
  allowOptionalExpiry,
  expiry,
  // Injectable for tests; FilePond itself is not usable under jsdom.
  createPond = createFilePond,
  navigate = navigateTo,
}) {
  const hostRef = useRef(null);
  const pondRef = useRef(null);

  // alert: null | { kind: "info" | "error", messages: string[], source }
  const [alert, setAlert] = useState(null);
  const [fileCount, setFileCount] = useState(0);
  const [hasValidationError, setHasValidationError] = useState(false);
  const [uploading, setUploading] = useState(false);
  // When optional expiry is disabled there is no checkbox and expiry is
  // always sent.
  const [enableExpiry, setEnableExpiry] = useState(!allowOptionalExpiry);
  const [expiryValue, setExpiryValue] = useState(() =>
    expiry?.initial ? toDateTimeLocalValue(new Date(expiry.initial)) : "",
  );
  const [zipName, setZipName] = useState(DEFAULT_ZIP_NAME);

  // FilePond callbacks are registered once, so they read form state from a
  // ref that is refreshed on every render.
  const latest = useRef({});
  latest.current = { enableExpiry, expiryValue };

  const clearErrorFrom = (source) =>
    setAlert((current) =>
      current?.kind === "error" && (source === null || current.source === source)
        ? null
        : current,
    );

  useEffect(() => {
    const pond = createPond({
      name: fileFieldName,
      maxFileSize,
      allowMultiple: true,
      allowProcess: false,
      allowRevert: false,
      credits: false,
      instantUpload: false,
      server: {
        process: {
          url: uploadUrl,
          method: "POST",
          withCredentials: false,
          headers: { "X-CSRFToken": getCsrfToken() },
          timeout: uploadTimeout * 1000,
          ondata: (formData) =>
            appendUploadFields(formData, {
              ...latest.current,
              csrfToken: getCsrfToken(),
            }),
          onload: (responseText) => {
            navigate(parseUploadResponse(responseText));
          },
          onerror: (responseText) => {
            const { messages, source } = parseUploadError(responseText);
            setAlert({ kind: "error", messages, source });
            setUploading(false);
          },
        },
        fetch: null,
        revert: null,
      },
    });
    pondRef.current = pond;
    hostRef.current.appendChild(pond.element);

    const syncFileCount = () => setFileCount(pond.getFiles().length);

    pond.on("addfile", (error) => {
      if (error) {
        setHasValidationError(true);
        setAlert({
          kind: "error",
          messages: [describeAddFileError(error)],
          source: "file",
        });
      } else {
        setHasValidationError(false);
        clearErrorFrom(null);
      }
      syncFileCount();
    });

    pond.on("removefile", () => {
      if (pond.getFiles().length === 0) {
        setHasValidationError(false);
        clearErrorFrom(null);
      }
      syncFileCount();
    });

    pond.on("updatefiles", syncFileCount);

    return () => {
      pond.destroy();
      pond.element?.remove();
      pondRef.current = null;
    };
    // The island's props come from the server and never change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleUpload = async () => {
    const pond = pondRef.current;
    setUploading(true);
    try {
      await combineFiles(pond, zipName);
    } catch (error) {
      console.error(error);
      setAlert({
        kind: "error",
        messages: [error?.main || GENERIC_UPLOAD_ERROR],
        source: error?.main ? "file" : "server",
      });
      setUploading(false);
      return;
    }

    setAlert({ kind: "info", messages: [STAY_ON_PAGE_MESSAGE], source: null });
    // FilePond also rejects this promise on server errors; those are already
    // reported to the user through the process.onerror callback.
    Promise.resolve(pond.processFiles()).catch(() => {});
  };

  const handleEnableExpiryChange = (checked) => {
    setEnableExpiry(checked);
    if (!checked) {
      clearErrorFrom("expiry");
    }
  };

  const handleExpiryChange = (value, input) => {
    setExpiryValue(value);
    const isValidDate = !Number.isNaN(new Date(value).getTime());
    if (isValidDate && input.checkValidity()) {
      clearErrorFrom("expiry");
    }
  };

  const uploadDisabled = hasValidationError || fileCount === 0 || uploading;

  return (
    <>
      {alert && <AlertBox kind={alert.kind} messages={alert.messages} />}

      <div ref={hostRef} data-testid="filepond-host" />

      <div className="flex flex-col py-2">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between w-full">
          <ExpiryPicker
            allowOptionalExpiry={allowOptionalExpiry}
            enableExpiry={enableExpiry}
            onEnableExpiryChange={handleEnableExpiryChange}
            value={expiryValue}
            onValueChange={handleExpiryChange}
            minIso={expiry?.min}
            maxIso={expiry?.max}
          />

          {fileCount > 1 && (
            <div className="flex items-center w-full xl:w-auto grow">
              <label htmlFor="zip-file-name" className="font-medium mr-2">
                Zip File Name:
              </label>
              <input
                id="zip-file-name"
                name="zip-file-name"
                className="rounded-l-lg p-2 border-2 bg-sky-100 border-sky-200 focus:outline-none focus:border-primary focus:ring-0 focus:rounded-l-lg grow"
                value={zipName}
                onChange={(event) => setZipName(event.target.value)}
              />
              <span className="rounded-r-lg p-2 border-y-2 border-r-2 bg-gray-100 border-gray-200">
                .zip
              </span>
            </div>
          )}

          <div className="flex justify-center xl:justify-end w-full xl:w-auto">
            <button
              id="upload-btn"
              type="button"
              className="btn-primary"
              disabled={uploadDisabled}
              onClick={handleUpload}
            >
              Upload
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
