const images = {{ images | tojson | safe }};
let currentPost = null;
let currentIndex = 0;
let isZoomed = false;

document.addEventListener('DOMContentLoaded', () => {
    setupUploadArea();
    setupSearch();
    checkEmptyFocus();
    checkHashOpen();
});

function findImage(id) { return images.find(img => img.id == id); }

function openModal(id) {
    const post = findImage(id);
    if (!post) return;
    currentPost = post;
    currentIndex = 0;
    updateModal();
    document.getElementById('imageModal').classList.add('show');
    document.body.style.overflow = 'hidden';
    resetZoom();
}

function closeModal() {
    const modal = document.getElementById('imageModal');
    modal.classList.remove('show');
    setTimeout(() => modal.style.display = 'none', 250);
    document.body.style.overflow = '';
}

function updateModal() {
    if (!currentPost) return;
    document.getElementById('modalTitle').textContent = currentPost.title;
    document.getElementById('modalDescription').textContent = currentPost.description || '';
    document.getElementById('modalDate').textContent = currentPost.created_at.slice(0,10);
    document.getElementById('deleteId').value = currentPost.id;
    document.getElementById('editId').value = currentPost.id;
    document.getElementById('editTitle').value = currentPost.title;
    document.getElementById('editDescription').value = currentPost.description || '';

    const paths = currentPost.image_path || [];
    document.getElementById('modalImage').src = '/static/uploads/' + paths[currentIndex];
    document.querySelectorAll('.carousel-prev, .carousel-next').forEach(b => 
        b.style.display = paths.length > 1 ? 'block' : 'none'
    );
    updateIndicators();
}

function updateIndicators() {
    const container = document.getElementById('carouselIndicators');
    container.innerHTML = '';
    if (!currentPost || currentPost.image_path.length <= 1) return;
    currentPost.image_path.forEach((_, i) => {
        const dot = document.createElement('div');
        dot.className = 'carousel-dot' + (i === currentIndex ? ' active' : '');
        dot.onclick = () => { currentIndex = i; updateModal(); resetZoom(); };
        container.appendChild(dot);
    });
}

function changeImage(dir) {
    if (!currentPost || currentPost.image_path.length <= 1) return;
    currentIndex = (currentIndex + dir + currentPost.image_path.length) % currentPost.image_path.length;
    updateModal();
    resetZoom();
}

function toggleZoom() {
    const side = document.getElementById('imageSide');
    isZoomed = !isZoomed;
    side.classList.toggle('zoomed', isZoomed);
    if (!isZoomed) side.scrollTo(0,0);
}

// Mouse wheel zoom
document.getElementById('imageSide').addEventListener('wheel', e => {
    if (!e.ctrlKey) return;
    e.preventDefault();
    toggleZoom();
});

// Upload form
document.getElementById('showUploadBtn').onclick = () => {
    const section = document.getElementById('uploadSection');
    section.classList.add('visible');
    section.scrollIntoView({ behavior: 'smooth' });
    document.getElementById('title').focus();
};

document.getElementById('cancelUpload').onclick = () => {
    document.getElementById('uploadSection').classList.remove('visible');
    document.getElementById('uploadForm').reset();
    document.getElementById('imagePreview').innerHTML = '';
};

function setupUploadArea() {
    const dropArea = document.getElementById('dropArea');
    const fileInput = document.getElementById('images');

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(ev => {
        dropArea.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); });
    });
    ['dragenter', 'dragover'].forEach(ev => {
        dropArea.addEventListener(ev, () => dropArea.classList.add('dragover'));
    });
    ['dragleave', 'drop'].forEach(ev => {
        dropArea.addEventListener(ev, () => dropArea.classList.remove('dragover'));
    });
    dropArea.addEventListener('drop', e => {
        fileInput.files = e.dataTransfer.files;
        previewImages({ target: fileInput });
    });
    fileInput.addEventListener('change', e => previewImages(e));
}

function previewImages(e) {
    const preview = document.getElementById('imagePreview');
    preview.innerHTML = '';
    for (const file of e.target.files) {
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = ev => {
                const img = document.createElement('img');
                img.src = ev.target.result;
                preview.appendChild(img);
            };
            reader.readAsDataURL(file);
        }
    }
}

function toggleEditMode() {
    document.getElementById('editForm').style.display =
        document.getElementById('editForm').style.display === 'block' ? 'none' : 'block';
}

function resetZoom() {
    isZoomed = false;
    document.getElementById('imageSide').classList.remove('zoomed');
}

function setupSearch() {
    document.getElementById('searchInput').addEventListener('input', e => {
        const term = e.target.value.toLowerCase();
        document.querySelectorAll('.gallery-item').forEach(item => {
            const text = item.textContent.toLowerCase();
            item.style.display = text.includes(term) ? '' : 'none';
        });
    });
}

// Open modal from URL hash (after upload)
function checkHashOpen() {
    if (location.hash) {
        const id = location.hash.slice(1);
        setTimeout(() => openModal(id), 400);
        history.replaceState(null, null, ' '); // clear hash
    }
}

function checkEmptyFocus() {
    if (images.length === 0) {
        setTimeout(() => document.getElementById('title')?.focus(), 200);
    }
}

document.getElementById('imageModal').addEventListener('click', e => {
    if (e.target === document.getElementById('imageModal')) closeModal();
});

// Keyboard
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeModal();
    if (e.key === 'ArrowLeft' && document.querySelector('.modal.show')) changeImage(-1);
    if (e.key === 'ArrowRight' && document.querySelector('.modal.show')) changeImage(1);
});
