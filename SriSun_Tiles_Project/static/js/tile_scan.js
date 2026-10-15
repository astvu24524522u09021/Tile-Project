(() => {
    const form = document.getElementById('tile-scan-form');
    if (!form) return;

    const camera = document.getElementById('tile-camera');
    const canvas = document.getElementById('tile-capture-canvas');
    const preview = document.getElementById('scan-preview');
    const placeholder = document.getElementById('scan-placeholder');
    const fileInput = document.getElementById('id_image');
    const status = document.getElementById('scan-status');
    const captureButton = document.getElementById('capture-tile');
    const analyzeButton = document.getElementById('analyze-tile');
    let stream = null;
    let previewUrl = null;

    const stopCamera = () => {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
        camera.srcObject = null;
        camera.hidden = true;
        captureButton.disabled = true;
    };

    const showImage = file => {
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        previewUrl = URL.createObjectURL(file);
        preview.src = previewUrl;
        preview.hidden = false;
        camera.hidden = true;
        placeholder.hidden = true;
        analyzeButton.disabled = false;
        status.textContent = 'Image ready. Select Analyze Tile to check the stored T001-T005 references.';
    };

    document.getElementById('open-camera').addEventListener('click', async () => {
        if (!navigator.mediaDevices?.getUserMedia) {
            status.textContent = 'Camera access is unavailable here. Use Upload Image instead.';
            return;
        }

        stopCamera();
        fileInput.value = '';
        analyzeButton.disabled = true;
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                audio: false,
                video: { facingMode: { ideal: 'environment' } },
            });
            camera.srcObject = stream;
            camera.hidden = false;
            preview.hidden = true;
            placeholder.hidden = true;
            captureButton.disabled = false;
            status.textContent = 'Camera ready. Center the tile and select Capture.';
        } catch (error) {
            status.textContent = 'Camera access was not available. Use Upload Image instead.';
        }
    });

    captureButton.addEventListener('click', () => {
        if (!stream || camera.videoWidth === 0) return;
        canvas.width = camera.videoWidth;
        canvas.height = camera.videoHeight;
        canvas.getContext('2d').drawImage(camera, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(blob => {
            if (!blob) {
                status.textContent = 'The image could not be captured. Please try again.';
                return;
            }
            const imageFile = new File([blob], 'tile-scan.jpg', { type: 'image/jpeg' });
            const transfer = new DataTransfer();
            transfer.items.add(imageFile);
            fileInput.files = transfer.files;
            stopCamera();
            showImage(imageFile);
        }, 'image/jpeg', 0.92);
    });

    document.getElementById('upload-tile').addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
        const imageFile = fileInput.files?.[0];
        if (!imageFile) return;
        stopCamera();
        showImage(imageFile);
    });

    form.addEventListener('submit', () => {
        stopCamera();
        analyzeButton.disabled = true;
        analyzeButton.textContent = 'Analyzing...';
    });

    window.addEventListener('pagehide', stopCamera);
})();