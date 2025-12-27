document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('search-text');
    const imageInput = document.getElementById('image-input');
    const imagePreviewContainer = document.getElementById('image-preview-container');
    const imagePreview = document.getElementById('image-preview');

    // Handle paste events on the document (or specifically the input)
    document.addEventListener('paste', (event) => {
        const items = (event.clipboardData || event.originalEvent.clipboardData).items;

        for (const item of items) {
            if (item.type.indexOf('image') !== -1) {
                const blob = item.getAsFile();

                // Create a FileList containing the pasted file to set on the input
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(blob);
                imageInput.files = dataTransfer.files;

                // Show preview
                const reader = new FileReader();
                reader.onload = (e) => {
                    imagePreview.src = e.target.result;
                    imagePreviewContainer.style.display = 'block';
                    searchInput.placeholder = "Image attached...";
                };
                reader.readAsDataURL(blob);

                // Prevent the default paste action (which might try to paste binary text)
                event.preventDefault();
                return;
            }
        }
    });

    window.clearImage = function() {
        imageInput.value = ''; // Clear file input
        imagePreviewContainer.style.display = 'none';
        imagePreview.src = '';
        searchInput.placeholder = "Search or paste an image...";
    };
});
