function setupFilepond(filepondElementName, expiryDatetimeElementName) {
    const inputElement = document.getElementsByName(filepondElementName)[0];

    const pond = FilePond.create(inputElement, {
        name: filepondElementName,
        allowMultiple: false,
        allowProcess: false,
        allowRevert: false,
        server: {
            process: {
                url: "./",
                method: "POST",
                withCredentials: false,
                headers: {
                    "X-CSRFToken": document.querySelector('input[name="csrfmiddlewaretoken"]').value
                },
                timeout: 7000,
                onload: null,
                onerror: null,
                ondata: (formData) => {
                    // Add the rest of the form data
                    formData.append("csrfmiddlewaretoken", document.querySelector('input[name="csrfmiddlewaretoken"]').value);
                    formData.append("expiry_datetime", document.querySelector('input[name="' + expiryDatetimeElementName + '"]').value);
                    return formData;
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
