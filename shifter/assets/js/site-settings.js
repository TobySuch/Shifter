function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

export async function cleanupExpiredFiles() {
  const button = this instanceof HTMLElement ? this : null;
  if (button) {
    button.disabled = true;
  }

  const result = await fetch("/api/cleanup-files", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    mode: "same-origin",
  });

  let resultJson = await result.json();
  const expiredFilesInfo = document.getElementById("expired-files-info");
  const expiredFilesInfoMsg = document.getElementById("expired-files-info-msg");

  if (resultJson.success) {
    if (resultJson.num_files_deleted === 1) {
      expiredFilesInfoMsg.innerHTML = `Successfully deleted 1 file.`;
    } else {
      expiredFilesInfoMsg.innerHTML = `Successfully deleted ${resultJson.num_files_deleted} files.`;
    }
    expiredFilesInfo.classList.remove("hidden");
    expiredFilesInfo.classList.remove("opacity-0");
  }

  if (button) {
    button.disabled = false;
  }
}

export async function copySiteInformation() {
  const button = this instanceof HTMLElement ? this : null;
  const siteInfoElement = document.getElementById("site-information-data");

  if (!siteInfoElement) {
    return;
  }

  let siteInfoText;
  try {
    siteInfoText = JSON.parse(siteInfoElement.textContent || '""');
  } catch (error) {
    console.error("Failed to parse site information data", error);
    if (button) {
      button.textContent = "Copy Failed";
      window.setTimeout(() => {
        button.textContent = "Copy Site Info";
      }, 2000);
    }
    return;
  }

  const originalText = button ? button.textContent : "";

  if (button) {
    button.disabled = true;
  }

  const resetButton = () => {
    if (!button) {
      return;
    }

    window.setTimeout(() => {
      button.textContent = originalText;
      button.disabled = false;
    }, 2000);
  };

  const clipboardApi = navigator.clipboard;
  if (!clipboardApi || typeof clipboardApi.writeText !== "function") {
    console.error("navigator.clipboard.writeText is unavailable in this browser");
    if (button) {
      button.textContent = "Copy Unavailable";
    }
    resetButton();
    return;
  }

  try {
    await clipboardApi.writeText(siteInfoText);
    if (button) {
      button.textContent = "Copied!";
    }
  } catch (error) {
    console.error("Failed to copy site information", error);
    if (button) {
      button.textContent = "Copy Failed";
    }
  }

  resetButton();
}

function initSiteSettings() {
  const cleanupButton = document.getElementById("cleanup-expired-files-btn");
  if (cleanupButton) {
    cleanupButton.addEventListener("click", function () {
      cleanupExpiredFiles.call(this);
    });
  }

  const copyButton = document.getElementById("copy-site-info-btn");
  if (copyButton) {
    copyButton.addEventListener("click", function () {
      copySiteInformation.call(this);
    });
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initSiteSettings);
} else {
  initSiteSettings();
}
