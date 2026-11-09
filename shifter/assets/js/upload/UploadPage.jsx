import { useEffect, useRef, useState } from "react";

import { toDateTimeLocalValue } from "../dates.js";
import AlertBox from "./AlertBox.jsx";
import { uploadStream } from "./chunked-upload.js";
import ExpiryPicker from "./ExpiryPicker.jsx";
import { createFilePond } from "./pond.js";
import UploadProgress from "./UploadProgress.jsx";
import {
  DEFAULT_ZIP_NAME,
  describeAddFileError,
  errorSource,
  expiryToIso,
  GENERIC_UPLOAD_ERROR,
  STAY_ON_PAGE_MESSAGE,
} from "./upload-logic.js";
import { buildUploadSource } from "./upload-source.js";

function navigateTo(url) {
  window.location.assign(url);
}

export default function UploadPage({
  initUrl,
  fileFieldName,
  maxFileSize,
  uploadTimeout,
  allowOptionalExpiry,
  expiry,
  // Injectable for tests; FilePond itself is not usable under jsdom.
  createPond = createFilePond,
  upload = uploadStream,
  navigate = navigateTo,
}) {
  const hostRef = useRef(null);
  const pondRef = useRef(null);

  // alert: null | { kind: "info" | "error", messages: string[], source }
  const [alert, setAlert] = useState(null);
  const [fileCount, setFileCount] = useState(0);
  const [hasValidationError, setHasValidationError] = useState(false);
  const [uploading, setUploading] = useState(false);
  // progress: null | { sent, total } in bytes
  const [progress, setProgress] = useState(null);
  // When optional expiry is disabled there is no checkbox and expiry is
  // always sent.
  const [enableExpiry, setEnableExpiry] = useState(!allowOptionalExpiry);
  const [expiryValue, setExpiryValue] = useState(() =>
    expiry?.initial ? toDateTimeLocalValue(new Date(expiry.initial)) : "",
  );
  const [zipName, setZipName] = useState(DEFAULT_ZIP_NAME);

  const clearErrorFrom = (source) =>
    setAlert((current) =>
      current?.kind === "error" && (source === null || current.source === source)
        ? null
        : current,
    );

  // FilePond is only the file picker: it validates sizes and lists the
  // selected files. Uploading is done by uploadStream below.
  useEffect(() => {
    const pond = createPond({
      name: fileFieldName,
      // maxFileSize is in bytes; a 1024 base matches the server's limit
      // and shows sizes the same way as the site settings.
      maxFileSize,
      fileSizeBase: 1024,
      allowMultiple: true,
      allowProcess: false,
      allowRevert: false,
      credits: false,
      instantUpload: false,
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
    pond.setOptions({ disabled: true });
    setAlert({ kind: "info", messages: [STAY_ON_PAGE_MESSAGE], source: null });

    try {
      const source = buildUploadSource(pond.getFiles(), zipName);
      setProgress({ sent: 0, total: source.size });
      const redirectUrl = await upload({
        initUrl,
        ...source,
        enableExpiry,
        expiryDatetime: expiryToIso(enableExpiry, expiryValue),
        timeoutMs: uploadTimeout * 1000,
        onProgress: (sent, total) => setProgress({ sent, total }),
      });
      navigate(redirectUrl);
    } catch (error) {
      console.error(error);
      const messages = error?.errors
        ? Object.values(error.errors).flat().map(String)
        : [error?.message || GENERIC_UPLOAD_ERROR];
      setAlert({
        kind: "error",
        messages,
        source: errorSource(error?.errors),
      });
      setProgress(null);
      setUploading(false);
      pond.setOptions({ disabled: false });
    }
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

      {progress && <UploadProgress {...progress} />}

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
                disabled={uploading}
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
