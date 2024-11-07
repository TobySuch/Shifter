import * as FilePond from "filepond";
import FilePondPluginFileValidateSize from "filepond-plugin-file-validate-size";
import JSZip from "jszip";
import "filepond/dist/filepond.min.css";

FilePond.registerPlugin(FilePondPluginFileValidateSize);

function showInfoBox(message) {
  const errorBox = document.getElementById("error-box");
  const infoBox = document.getElementById("info-box");
  const errorBoxMessage = document.getElementById("error-box-message");
  const infoBoxMessage = document.getElementById("info-box-message");
  errorBoxMessage.innerHTML = "";
  infoBoxMessage.innerHTML = message;
  errorBox.classList.add("hidden");
  infoBox.classList.remove("hidden");
}

function showErrorBox(message) {
  const errorBox = document.getElementById("error-box");
  const infoBox = document.getElementById("info-box");
  const errorBoxMessage = document.getElementById("error-box-message");
  const infoBoxMessage = document.getElementById("info-box-message");
  infoBoxMessage.innerHTML = "";
  errorBoxMessage.innerHTML = message;
  infoBox.classList.add("hidden");
  errorBox.classList.remove("hidden");
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
      await pond.addFile(
        new File([blob], "combined.zip", { type: "application/zip" })
      );
    });
  }

  // If there is only one file, do nothing
  return Promise.resolve();
}

export function setupFilepond(
  filepondElementName,
  expiryDatetimeElementName,
  max_file_size
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
            'input[name="csrfmiddlewaretoken"]'
          ).value,
        },
        timeout: 300 * 1000, // 5 minutes
        ondata: (formData) => {
          let expiryFormField = document.querySelector(
            'input[name="' + expiryDatetimeElementName + '"]'
          );
          let expiryDateTime = new Date(expiryFormField.value);

          // Add the rest of the form data
          formData.append(
            "csrfmiddlewaretoken",
            document.querySelector('input[name="csrfmiddlewaretoken"]').value
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
          showErrorBox(errorMsg);
        },
      },
      fetch: null,
      revert: null,
    },
    instantUpload: false,
  });
  const uploadButton = document.getElementById("upload-btn");

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
}
