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
  const alertsStore = window.Alpine?.store("siteSettingsAlerts") || null;
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
  if (resultJson.success) {
    if (alertsStore) {
      const message =
        resultJson.num_files_deleted === 1
          ? "Successfully deleted 1 file."
          : `Successfully deleted ${resultJson.num_files_deleted} files.`;
      alertsStore.setExpiredInfo(message);
    }
  }

  if (button) {
    button.disabled = false;
  }
}

export async function copySiteInformation() {
  const button = this instanceof HTMLElement ? this : null;
  const copyStore = window.Alpine?.store("siteSettingsCopy") || null;
  const siteInfoElement = document.getElementById("site-information-data");

  if (!siteInfoElement) {
    return;
  }

  let siteInfoText;
  try {
    siteInfoText = JSON.parse(siteInfoElement.textContent || '""');
  } catch (error) {
    console.error("Failed to parse site information data", error);
    if (copyStore) {
      copyStore.setStatus("Copy Failed", true);
      copyStore.resetAfterDelay();
    } else if (button) {
      button.textContent = "Copy Failed";
      window.setTimeout(() => {
        button.textContent = "Copy Site Info";
      }, 2000);
    }
    return;
  }

  const originalText = button ? button.textContent : "Copy Site Info";
  if (copyStore) {
    copyStore.setStatus(copyStore.label || originalText, true);
  } else if (button) {
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
    if (copyStore) {
      copyStore.setStatus("Copy Unavailable", true);
      copyStore.resetAfterDelay();
    } else if (button) {
      button.textContent = "Copy Unavailable";
      resetButton();
    }
    return;
  }

  try {
    await clipboardApi.writeText(siteInfoText);
    if (copyStore) {
      copyStore.setStatus("Copied!", true);
      copyStore.resetAfterDelay();
    } else if (button) {
      button.textContent = "Copied!";
      resetButton();
    }
  } catch (error) {
    console.error("Failed to copy site information", error);
    if (copyStore) {
      copyStore.setStatus("Copy Failed", true);
      copyStore.resetAfterDelay();
    } else if (button) {
      button.textContent = "Copy Failed";
      resetButton();
    }
  }
}

document.addEventListener("alpine:init", () => {
  if (!window.Alpine) {
    return;
  }

  window.Alpine.store("siteSettingsAlerts", {
    showExpiredInfo: false,
    expiredInfoMessage: "",
    setExpiredInfo(message) {
      this.expiredInfoMessage = message;
      this.showExpiredInfo = true;
    },
    clearExpiredInfo() {
      this.expiredInfoMessage = "";
      this.showExpiredInfo = false;
    },
  });

  window.Alpine.store("siteSettingsCopy", {
    label: "Copy Site Info",
    disabled: false,
    _resetTimer: null,
    setStatus(label, disabled) {
      this.label = label;
      this.disabled = disabled;
      if (this._resetTimer) {
        window.clearTimeout(this._resetTimer);
        this._resetTimer = null;
      }
    },
    resetAfterDelay(delayMs = 2000) {
      if (this._resetTimer) {
        window.clearTimeout(this._resetTimer);
      }
      this._resetTimer = window.setTimeout(() => {
        this.label = "Copy Site Info";
        this.disabled = false;
        this._resetTimer = null;
      }, delayMs);
    },
  });
});

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
