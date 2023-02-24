function setupFilepond(filepondElementName, expiryDatetimeElementName) {
    const inputElement = document.getElementsByName(filepondElementName)[0];

    const pond = FilePond.create(inputElement, {
        name: filepondElementName,
        allowMultiple: false,
        allowProcess: false,
        allowRevert: false,
        credits: false,
        server: {
            process: {
                url: "./",
                method: "POST",
                withCredentials: false,
                headers: {
                    "X-CSRFToken": document.querySelector('input[name="csrfmiddlewaretoken"]').value
                },
                timeout: 300 * 1000, // 5 minutes
                onload: null,
                onerror: null,
                ondata: (formData) => {
                    // Add the rest of the form data
                    formData.append("csrfmiddlewaretoken", document.querySelector('input[name="csrfmiddlewaretoken"]').value);
                    formData.append("expiry_datetime", document.querySelector('input[name="' + expiryDatetimeElementName + '"]').value);
                    return formData;
                },
                onload(response) {
                    redirectUrl = JSON.parse(response).redirect_url;
                    window.location.href = redirectUrl;
                },
                onerror: (response) => {
                    console.error(response);
                    const errorBox = document.getElementById('error-box');
                    document.getElementById('error-box').innerHTML = '';

                    rObj = JSON.parse(response);
                    for (const [key, value] of Object.entries(rObj.errors)) {
                        errorBox.innerHTML += value + '<br>';
                    }
                }
            },
            fetch: null,
            revert: null
        },
        instantUpload: false
    });
    const uploadButton = document.getElementById('upload-btn');

    uploadButton.addEventListener('click', () => {
        pond.processFiles();
    });
}
