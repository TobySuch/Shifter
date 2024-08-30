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
  this.disabled = true;

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

  this.disabled = false;
}
