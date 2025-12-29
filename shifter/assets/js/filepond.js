import * as FilePond from "filepond";
import FilePondPluginFileValidateSize from "filepond-plugin-file-validate-size";
import JSZip from "jszip";
import "filepond/dist/filepond.min.css";

FilePond.registerPlugin(FilePondPluginFileValidateSize);

function registerAlpineStores() {
  if (!window.Alpine) {
    return;
  }

  window.Alpine.store("uploadAlerts", {
    showInfo: false,
    showError: false,
    infoMessage: "",
    errorMessage: "",
    setInfo(message) {
      this.infoMessage = message;
      this.errorMessage = "";
      this.showError = false;
      this.showInfo = true;
    },
    setError(message) {
      this.errorMessage = message;
      this.infoMessage = "";
      this.showInfo = false;
      this.showError = true;
    },
    clear() {
      this.infoMessage = "";
      this.errorMessage = "";
      this.showInfo = false;
      this.showError = false;
    },
  });

  window.Alpine.store("uploadState", {
    showZipName: false,
  });
}

// Register stores immediately if Alpine has already started
if (window.Alpine && !window.Alpine.version.includes("loading")) {
  registerAlpineStores();
} else {
  // Otherwise wait for alpine:init event
  document.addEventListener("alpine:init", registerAlpineStores);
}

function getUploadAlertsStore() {
  if (!window.Alpine) {
    return null;
  }

  return window.Alpine.store("uploadAlerts");
}

function getUploadStateStore() {
  if (!window.Alpine) {
    return null;
  }

  return window.Alpine.store("uploadState");
}

function showInfoBox(message) {
  const alerts = getUploadAlertsStore();
  if (!alerts) {
    return;
  }

  alerts.setInfo(message);
}

function showErrorBox(message) {
  const alerts = getUploadAlertsStore();
  if (!alerts) {
    return;
  }

  alerts.setError(message);
}

function combineFiles(pond) {
  let files = pond.getFiles();

  // If there are no files, do nothing
  if (files.length === 0) {
    return Promise.reject("Select at least one file to upload");
  }

  // If there is more than one file, zip them into one file
  if (files.length > 1) {
    console.debug("Combining files");

    const zip = new JSZip();
    const promises = [];
    files.forEach((file) => {
      const promise = new Promise((resolve, reject) => {
        zip.file(file.filename, file.file, { binary: true });
        resolve();
      });
      promises.push(promise);
    });

    return Promise.all(promises).then(async () => {
      await pond.removeFiles();
      let blob = await zip.generateAsync({ type: "blob" });
      let zipFileNameFormElement = document.getElementById("zip-file-name");
      let zipFileName = zipFileNameFormElement.value;
      await pond.addFile(
        new File([blob], zipFileName + ".zip", { type: "application/zip" }),
      );
    });
  }

  // If there is only one file, do nothing
  return Promise.resolve();
}

function handleFilesChanged(pond) {
  const numFiles = pond.getFiles().length;
  const uploadState = getUploadStateStore();

  if (uploadState) {
    uploadState.showZipName = numFiles > 1;
  }
}

export function setupFilepond(
  filepondElementName,
  expiryDatetimeElementName,
  max_file_size,
) {
  const inputElement = document.getElementsByName(filepondElementName)[0];

  const pond = FilePond.create(inputElement, {
    name: filepondElementName,
    maxFileSize: max_file_size,
    allowMultiple: true,
    allowProcess: false,
    allowRevert: false,
    credits: false,
    server: {
      process: {
        url: "./",
        method: "POST",
        withCredentials: false,
        headers: {
          "X-CSRFToken": document.querySelector(
            'input[name="csrfmiddlewaretoken"]',
          ).value,
        },
        timeout: 300 * 1000, // 5 minutes
        ondata: (formData) => {
          let expiryFormField = document.querySelector(
            'input[name="' + expiryDatetimeElementName + '"]',
          );
          let expiryDateTime = new Date(expiryFormField.value);

          // Add the rest of the form data
          formData.append(
            "csrfmiddlewaretoken",
            document.querySelector('input[name="csrfmiddlewaretoken"]').value,
          );
          formData.append("expiry_datetime", expiryDateTime.toISOString());
          return formData;
        },
        onload: (response) => {
          const redirectUrl = JSON.parse(response).redirect_url;
          window.location.href = redirectUrl;
        },
        onerror: (response) => {
          console.error(response);
          const rObj = JSON.parse(response);
          let errorMsg = "";
          for (const [key, value] of Object.entries(rObj.errors)) {
            errorMsg += value + "<br>";
          }
          if (rObj.errors?.expiry_datetime) {
            lastErrorSource = "expiry";
          } else if (rObj.errors?.file_content) {
            lastErrorSource = "file";
          } else {
            lastErrorSource = "server";
          }
          showErrorBox(errorMsg);
        },
      },
      fetch: null,
      revert: null,
    },
    instantUpload: false,
  });
  const uploadButton = document.getElementById("upload-btn");
  let hasValidationError = false;
  let lastErrorSource = null;

  function updateUploadButtonState() {
    uploadButton.disabled = hasValidationError || pond.getFiles().length === 0;
  }

  const expiryFormField = document.querySelector(
    'input[name="' + expiryDatetimeElementName + '"]',
  );
  if (expiryFormField) {
    const handleExpiryChange = () => {
      updateUploadButtonState();
      const expiryDateTime = new Date(expiryFormField.value);
      const isValidDate = !Number.isNaN(expiryDateTime.getTime());
      if (isValidDate && expiryFormField.checkValidity()) {
        const alerts = getUploadAlertsStore();
        if (alerts && alerts.showError && lastErrorSource === "expiry") {
          alerts.clear();
          lastErrorSource = null;
        }
      }
    };
    expiryFormField.addEventListener("input", handleExpiryChange);
    expiryFormField.addEventListener("change", handleExpiryChange);
  }

  uploadButton.addEventListener("click", () => {
    combineFiles(pond)
      .then(() => {
        console.debug("Uploading file");
        showInfoBox("Stay on this page until upload is finished.");
        uploadButton.disabled = true;
        pond.processFiles();
      })
      .catch((error) => {
        console.error(error);
        showErrorBox("Error during upload.");
      });
  });

  pond.on("addfile", (error) => {
    if (error) {
      const errorMessage =
        typeof error === "string"
          ? error
          : error?.main || error?.message || "File could not be added.";
      hasValidationError = true;
      lastErrorSource = "file";
      showErrorBox(errorMessage);
      updateUploadButtonState();
      return;
    }

    hasValidationError = false;
    const alerts = getUploadAlertsStore();
    if (alerts && alerts.showError) {
      alerts.clear();
      lastErrorSource = null;
    }
    updateUploadButtonState();
  });

  pond.on("removefile", () => {
    if (pond.getFiles().length === 0) {
      hasValidationError = false;
      const alerts = getUploadAlertsStore();
      if (alerts && alerts.showError) {
        alerts.clear();
        lastErrorSource = null;
      }
    }
    updateUploadButtonState();
  });

  pond.on("updatefiles", () => {
    handleFilesChanged(pond);
    updateUploadButtonState();
  });

  updateUploadButtonState();
}

function autoInitFilepond() {
  const host = document.querySelector("[data-filepond]");
  if (!host) {
    return;
  }

  const { fileField, expiryField, maxSize } = host.dataset;
  if (!fileField || !expiryField || !maxSize) {
    console.warn("Filepond init skipped: missing data attributes.");
    return;
  }

  setupFilepond(fileField, expiryField, maxSize);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", autoInitFilepond);
} else {
  autoInitFilepond();
}
