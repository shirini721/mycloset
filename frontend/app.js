// MyCloset Frontend Application

const API_BASE = '';

// State
let currentTab = 'wardrobe';
let wardrobeItems = [];

// DOM Elements
const tabs = document.querySelectorAll('.tab');
const tabContents = document.querySelectorAll('.tab-content');
const wardrobeGrid = document.getElementById('wardrobe-grid');
const categoryFilter = document.getElementById('category-filter');
const recommendForm = document.getElementById('recommend-form');
const addForm = document.getElementById('add-form');
const imageInput = document.getElementById('image-input');
const uploadArea = document.getElementById('upload-area');
const uploadPlaceholder = document.getElementById('upload-placeholder');
const imagePreview = document.getElementById('image-preview');
const uploadBtn = document.getElementById('upload-btn');
const uploadStatus = document.getElementById('upload-status');
const itemModal = document.getElementById('item-modal');
const modalBody = document.getElementById('modal-body');
const modalClose = document.querySelector('.modal-close');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initUploadArea();
    initForms();
    initModal();
    loadWardrobe();
});

// Tab Navigation
function initTabs() {
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.dataset.tab;
            switchTab(tabId);
        });
    });
}

function switchTab(tabId) {
    currentTab = tabId;

    tabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabId);
    });

    tabContents.forEach(content => {
        content.classList.toggle('active', content.id === tabId);
    });

    if (tabId === 'wardrobe') {
        loadWardrobe();
    }
}

// Wardrobe
async function loadWardrobe(category = '') {
    try {
        const url = category
            ? `${API_BASE}/api/clothes?category=${category}`
            : `${API_BASE}/api/clothes`;

        const response = await fetch(url);
        wardrobeItems = await response.json();
        renderWardrobe();
    } catch (error) {
        console.error('Error loading wardrobe:', error);
        wardrobeGrid.innerHTML = '<div class="empty-state"><p>Error loading wardrobe</p></div>';
    }
}

function renderWardrobe() {
    if (wardrobeItems.length === 0) {
        wardrobeGrid.innerHTML = `
            <div class="empty-state">
                <p>Your wardrobe is empty!</p>
                <p>Start by adding some clothes.</p>
            </div>
        `;
        return;
    }

    wardrobeGrid.innerHTML = wardrobeItems.map(item => `
        <div class="clothing-card" onclick="showItemDetails(${item.id})">
            <img src="${item.image_path || '/static/placeholder.png'}" alt="${item.name}" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22><rect fill=%22%23e1e8ed%22 width=%22200%22 height=%22200%22/><text fill=%22%237f8c8d%22 font-family=%22sans-serif%22 font-size=%2214%22 x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22>No Image</text></svg>'">
            <div class="clothing-card-info">
                <div class="clothing-card-name">${item.name}</div>
                <div class="clothing-card-category">${item.subcategory || item.category}</div>
                <div class="clothing-card-tags">
                    <span class="tag style">${item.style || 'Casual'}</span>
                    <span class="tag">${item.color || 'Unknown'}</span>
                </div>
            </div>
        </div>
    `).join('');
}

// Category Filter
categoryFilter.addEventListener('change', (e) => {
    loadWardrobe(e.target.value);
});

// Upload Area
function initUploadArea() {
    uploadArea.addEventListener('click', () => imageInput.click());

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0 && files[0].type.startsWith('image/')) {
            handleImageSelect(files[0]);
        }
    });

    imageInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleImageSelect(e.target.files[0]);
        }
    });
}

function handleImageSelect(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        imagePreview.src = e.target.result;
        imagePreview.classList.remove('hidden');
        uploadPlaceholder.classList.add('hidden');
        uploadBtn.disabled = false;
    };
    reader.readAsDataURL(file);
}

// Forms
function initForms() {
    addForm.addEventListener('submit', handleAddItem);
    recommendForm.addEventListener('submit', handleGetRecommendations);
}

async function handleAddItem(e) {
    e.preventDefault();

    const file = imageInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('image', file);

    const customName = document.getElementById('item-name').value;
    if (customName) {
        formData.append('name', customName);
    }

    uploadBtn.disabled = true;
    uploadBtn.textContent = 'Analyzing...';
    uploadStatus.classList.remove('hidden', 'success', 'error');
    uploadStatus.textContent = 'Uploading and analyzing your item...';

    try {
        const response = await fetch(`${API_BASE}/api/clothes`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Upload failed');
        }

        const item = await response.json();

        uploadStatus.classList.add('success');
        uploadStatus.innerHTML = `
            <strong>Success!</strong> Added "${item.name}" to your wardrobe.<br>
            <small>Category: ${item.subcategory || item.category} | Style: ${item.style} | Color: ${item.color}</small>
        `;

        // Reset form
        setTimeout(() => {
            imageInput.value = '';
            imagePreview.classList.add('hidden');
            uploadPlaceholder.classList.remove('hidden');
            document.getElementById('item-name').value = '';
            uploadBtn.textContent = 'Upload & Analyze';
        }, 2000);

    } catch (error) {
        console.error('Error uploading item:', error);
        uploadStatus.classList.add('error');
        uploadStatus.textContent = 'Error uploading item. Please try again.';
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Upload & Analyze';
    }
}

async function handleGetRecommendations(e) {
    e.preventDefault();

    const eventType = document.getElementById('event-type').value;
    const location = document.getElementById('location').value;
    const manualWeather = document.getElementById('manual-weather').value;
    const preferences = document.getElementById('preferences').value;

    if (!eventType) {
        alert('Please select an occasion');
        return;
    }

    const loading = document.getElementById('loading');
    const results = document.getElementById('recommendations-results');

    loading.classList.remove('hidden');
    results.classList.add('hidden');

    try {
        const response = await fetch(`${API_BASE}/api/recommendations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                event_type: eventType,
                location: location || null,
                weather: manualWeather || null,
                additional_preferences: preferences || null
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get recommendations');
        }

        const data = await response.json();
        displayRecommendations(data);

    } catch (error) {
        console.error('Error getting recommendations:', error);
        alert(`Error: ${error.message}`);
    } finally {
        loading.classList.add('hidden');
    }
}

function displayRecommendations(data) {
    const results = document.getElementById('recommendations-results');
    const weatherInfo = document.getElementById('weather-info');
    const outfitsContainer = document.getElementById('outfits-container');

    // Display weather info
    const weather = data.weather_info;
    weatherInfo.innerHTML = `
        <h3>Weather in ${weather.location}</h3>
        <div class="weather-details">
            <div class="weather-detail">
                <span>${weather.temperature}°F</span>
                <small>(feels like ${weather.feels_like}°F)</small>
            </div>
            <div class="weather-detail">
                <span>${weather.description}</span>
            </div>
            ${weather.is_rainy ? '<div class="weather-detail"><span>Rain expected</span></div>' : ''}
        </div>
        <p style="margin-top: 12px; opacity: 0.9;">${weather.clothing_recommendation}</p>
    `;

    // Display outfits
    if (data.recommendations.length === 0) {
        outfitsContainer.innerHTML = `
            <div class="empty-state">
                <p>No outfit recommendations found.</p>
                <p>Try adding more clothes to your wardrobe!</p>
            </div>
        `;
    } else {
        outfitsContainer.innerHTML = data.recommendations.map((outfit, index) => `
            <div class="outfit-card">
                <div class="outfit-header">
                    <h3 class="outfit-name">${outfit.outfit_name}</h3>
                    <span class="tag style">Outfit ${index + 1}</span>
                </div>
                <div class="outfit-items">
                    ${outfit.items.map(item => `
                        <div class="outfit-item" onclick="showItemDetails(${item.id})">
                            <img src="${item.image_path || ''}" alt="${item.name}" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22120%22 height=%22120%22><rect fill=%22%23e1e8ed%22 width=%22120%22 height=%22120%22/><text fill=%22%237f8c8d%22 font-family=%22sans-serif%22 font-size=%2212%22 x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22>No Image</text></svg>'">
                            <div class="outfit-item-name">${item.name}</div>
                        </div>
                    `).join('')}
                </div>
                <div class="outfit-reasoning">
                    <h4>Why this works:</h4>
                    <p>${outfit.reasoning}</p>
                </div>
                ${outfit.style_notes ? `<p class="outfit-style-notes">${outfit.style_notes}</p>` : ''}
            </div>
        `).join('');
    }

    results.classList.remove('hidden');
}

// Modal
function initModal() {
    modalClose.addEventListener('click', closeModal);
    itemModal.addEventListener('click', (e) => {
        if (e.target === itemModal) closeModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
}

function showItemDetails(itemId) {
    const item = wardrobeItems.find(i => i.id === itemId);
    if (!item) {
        // Fetch item if not in current list
        fetch(`${API_BASE}/api/clothes/${itemId}`)
            .then(res => res.json())
            .then(item => renderItemModal(item))
            .catch(err => console.error('Error fetching item:', err));
        return;
    }
    renderItemModal(item);
}

function renderItemModal(item) {
    modalBody.innerHTML = `
        <img src="${item.image_path || ''}" alt="${item.name}" onerror="this.style.display='none'">
        <h3>${item.name}</h3>
        <div class="item-details">
            <div class="item-detail">
                <div class="item-detail-label">Category</div>
                <div class="item-detail-value">${item.subcategory || item.category}</div>
            </div>
            <div class="item-detail">
                <div class="item-detail-label">Color</div>
                <div class="item-detail-value">${item.color || 'Unknown'}</div>
            </div>
            <div class="item-detail">
                <div class="item-detail-label">Material</div>
                <div class="item-detail-value">${item.material || 'Unknown'}</div>
            </div>
            <div class="item-detail">
                <div class="item-detail-label">Pattern</div>
                <div class="item-detail-value">${item.pattern || 'Solid'}</div>
            </div>
            <div class="item-detail">
                <div class="item-detail-label">Style</div>
                <div class="item-detail-value">${item.style || 'Casual'}</div>
            </div>
            <div class="item-detail">
                <div class="item-detail-label">Weather</div>
                <div class="item-detail-value">${(item.weather_suitability || []).join(', ') || 'Any'}</div>
            </div>
        </div>
        ${item.description ? `
            <div class="item-description">
                <strong>Description:</strong> ${item.description}
            </div>
        ` : ''}
        <div class="item-detail" style="margin-bottom: 20px;">
            <div class="item-detail-label">Good for</div>
            <div class="item-detail-value">${(item.occasion_suitability || []).join(', ') || 'Any occasion'}</div>
        </div>
        <div class="modal-actions">
            <button class="btn btn-danger" onclick="deleteItem(${item.id})">Delete Item</button>
        </div>
    `;
    itemModal.classList.remove('hidden');
}

function closeModal() {
    itemModal.classList.add('hidden');
}

async function deleteItem(itemId) {
    if (!confirm('Are you sure you want to delete this item?')) return;

    try {
        const response = await fetch(`${API_BASE}/api/clothes/${itemId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to delete item');
        }

        closeModal();
        loadWardrobe();

    } catch (error) {
        console.error('Error deleting item:', error);
        alert('Error deleting item. Please try again.');
    }
}

// Make functions globally available
window.showItemDetails = showItemDetails;
window.deleteItem = deleteItem;
