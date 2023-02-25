function combineFiles(pond) {
    let files = pond.getFiles();

    // If there is more than one file, zip them into one file
    if (files.length > 1) {
        console.debug("Combining files")
        
        const zip = new JSZip();
        const promises = [];
        files.forEach((file) => {
            const promise = new Promise((resolve, reject) => {
                zip.file(file.filename, file.file, {binary: true});
                resolve();
            });
            promises.push(promise);
        });

        return Promise.all(promises)
            .then(async () => {
                await pond.removeFiles()
                let blob = await zip.generateAsync({type: "blob"})
                await pond.addFile(new File([blob], 'combined.zip', { type: 'application/zip' }));
            })
    }

    // If there is only one file, do nothing
    return Promise.resolve();
}

function setupFilepond(filepondElementName, expiryDatetimeElementName) {
    const inputElement = document.getElementsByName(filepondElementName)[0];

    const pond = FilePond.create(inputElement, {
        name: filepondElementName,
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
                    "X-CSRFToken": document.querySelector('input[name="csrfmiddlewaretoken"]').value
                },
                timeout: 300 * 1000, // 5 minutes
                ondata: (formData) => {
                    // Add the rest of the form data
                    formData.append("csrfmiddlewaretoken", document.querySelector('input[name="csrfmiddlewaretoken"]').value);
                    formData.append("expiry_datetime", document.querySelector('input[name="' + expiryDatetimeElementName + '"]').value);
                    return formData;
                },
                onload: (response) => {
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
        combineFiles(pond).then(() => {
            console.debug("Uploading file")
            pond.processFiles();
        });
    });
}
