document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-text');
    const imageInput = document.getElementById('image-input');
    const imagePreviewContainer = document.getElementById('image-preview-container');
    const imagePreview = document.getElementById('image-preview');
    const spinnerOverlay = document.getElementById('spinner-overlay');
    const searchButton = document.getElementById('btn-search');
    const derpyButton = document.getElementById('btn-derpy');

    // Handle paste events
    document.addEventListener('paste', (event) => {
        const items = (event.clipboardData || event.originalEvent.clipboardData).items;

        for (const item of items) {
            if (item.type.indexOf('image') !== -1) {
                const blob = item.getAsFile();

                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(blob);
                imageInput.files = dataTransfer.files;

                const reader = new FileReader();
                reader.onload = (e) => {
                    imagePreview.src = e.target.result;
                    imagePreviewContainer.style.display = 'block';
                    searchInput.placeholder = "Image attached...";
                };
                reader.readAsDataURL(blob);

                event.preventDefault();
                return;
            }
        }
    });

    window.clearImage = function() {
        imageInput.value = '';
        imagePreviewContainer.style.display = 'none';
        imagePreview.src = '';
        searchInput.placeholder = "Search or paste an image...";
    };

    // Handle Form Submission (Loading State)
    searchForm.addEventListener('submit', (event) => {
        // Determine which button triggered the submit if possible (simplest is just to lock all)
        // If "I'm Feeling Derpy" was clicked, we technically don't need to lock the input value,
        // but locking the UI is good feedback.

        // Disable inputs and buttons (use readOnly for text input so value is sent)
        searchInput.readOnly = true;
        searchButton.disabled = true;
        derpyButton.disabled = true;

        // Show spinner
        spinnerOverlay.style.display = 'flex';
    });

    // Allow submitting with the "I'm Feeling Derpy" button specifically
    derpyButton.addEventListener('click', () => {
         // We don't need special JS logic here as the form will submit with name="derpy"
         // The submit event listener above will catch it.
    });
});
