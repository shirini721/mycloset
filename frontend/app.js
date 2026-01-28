// MyCloset Frontend Application

const API_BASE = '';

// State
let currentTab = 'wardrobe';
let wardrobeItems = [];
let selectedFile = null;  // Store the selected file for upload

// DOM Elements - initialized in init()
let tabs, tabContents, wardrobeGrid, categoryFilter, recommendForm, addForm;
let imageInput, uploadArea, uploadPlaceholder, imagePreview, uploadBtn, uploadStatus;
let itemModal, modalBody, modalClose;

// Toggle dropdown menu
function toggleDropdown(show = null) {
    const menu = document.getElementById('more-actions-menu');
    if (menu) {
        if (show === null) {
            menu.classList.toggle('show');
        } else if (show) {
            menu.classList.add('show');
        } else {
            menu.classList.remove('show');
        }
    }
}

// Initialize
function init() {
    console.log('[MyCloset] Initializing...');

    // Get DOM elements
    tabs = document.querySelectorAll('.tab');
    tabContents = document.querySelectorAll('.tab-content');
    wardrobeGrid = document.getElementById('wardrobe-grid');
    categoryFilter = document.getElementById('category-filter');
    recommendForm = document.getElementById('recommend-form');
    addForm = document.getElementById('add-form');
    imageInput = document.getElementById('image-input');
    uploadArea = document.getElementById('upload-area');
    uploadPlaceholder = document.getElementById('upload-placeholder');
    imagePreview = document.getElementById('image-preview');
    uploadBtn = document.getElementById('upload-btn');
    uploadStatus = document.getElementById('upload-status');
    itemModal = document.getElementById('item-modal');
    modalBody = document.getElementById('modal-body');
    modalClose = document.querySelector('.modal-close');

    // Check critical elements exist
    if (!uploadArea || !imageInput || !uploadBtn || !addForm) {
        console.error('[MyCloset] Critical DOM elements not found!');
        return;
    }

    console.log('[MyCloset] DOM elements found, setting up...');

    initTabs();
    initCategoryFilter();
    initUploadArea();
    initForms();
    initModal();
    initGmailSection();
    loadWardrobe();

    console.log('[MyCloset] Initialization complete');
}

// Run init when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

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

// Category Filter - moved into initForms()
function initCategoryFilter() {
    if (categoryFilter) {
        categoryFilter.addEventListener('change', (e) => {
            loadWardrobe(e.target.value);
        });
    }
}

// Upload Area
function initUploadArea() {
    // Click to open file picker
    uploadArea.addEventListener('click', (e) => {
        // Don't trigger if clicking on the preview image
        if (e.target !== imagePreview) {
            imageInput.click();
        }
    });

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
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
    selectedFile = file;  // Store the file globally
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
    // Note: recommendForm was replaced with chat-form, handled in initChat()
}

async function handleAddItem(e) {
    e.preventDefault();

    // Use selectedFile (works for both click and drag-drop)
    const file = selectedFile || imageInput.files[0];
    if (!file) {
        alert('Please select an image first');
        return;
    }

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
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Upload failed');
        }

        const item = await response.json();

        uploadStatus.classList.add('success');
        uploadStatus.innerHTML = `
            <strong>Success!</strong> Added "${item.name}" to your wardrobe.<br>
            <small>Category: ${item.subcategory || item.category} | Style: ${item.style} | Color: ${item.color}</small>
        `;

        // Reset form
        setTimeout(() => {
            selectedFile = null;
            imageInput.value = '';
            imagePreview.classList.add('hidden');
            uploadPlaceholder.classList.remove('hidden');
            document.getElementById('item-name').value = '';
            uploadBtn.textContent = 'Upload & Analyze';
            uploadBtn.disabled = true;
        }, 2000);

    } catch (error) {
        console.error('Error uploading item:', error);
        uploadStatus.classList.add('error');
        uploadStatus.textContent = `Error: ${error.message}. Please try again.`;
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
window.importFromEmail = importFromEmail;

// ============ Gmail Import Functions ============

async function checkGmailStatus() {
    const statusDiv = document.getElementById('gmail-status');
    const connectDiv = document.getElementById('gmail-connect');
    const connectedDiv = document.getElementById('gmail-connected');
    const setupDiv = document.getElementById('gmail-setup-required');

    try {
        const response = await fetch(`${API_BASE}/api/gmail/status`);
        const data = await response.json();

        statusDiv.querySelector('.gmail-loading').classList.add('hidden');

        if (!data.credentials_configured) {
            // Show setup instructions
            setupDiv.classList.remove('hidden');
            connectDiv.classList.add('hidden');
            connectedDiv.classList.add('hidden');
        } else if (data.connected) {
            // Show connected state
            connectedDiv.classList.remove('hidden');
            connectDiv.classList.add('hidden');
            setupDiv.classList.add('hidden');
        } else {
            // Show connect button
            connectDiv.classList.remove('hidden');
            connectedDiv.classList.add('hidden');
            setupDiv.classList.add('hidden');
        }
    } catch (error) {
        console.error('Error checking Gmail status:', error);
        statusDiv.innerHTML = '<p class="error">Error checking Gmail status</p>';
    }
}

async function connectGmail() {
    try {
        const response = await fetch(`${API_BASE}/api/gmail/auth`);
        const data = await response.json();

        if (data.auth_url) {
            // Redirect to Google OAuth
            window.location.href = data.auth_url;
        } else {
            alert('Failed to get authorization URL');
        }
    } catch (error) {
        console.error('Error connecting Gmail:', error);
        alert('Error connecting to Gmail');
    }
}

async function disconnectGmail() {
    if (!confirm('Are you sure you want to disconnect Gmail?')) return;

    try {
        await fetch(`${API_BASE}/api/gmail/disconnect`, { method: 'POST' });
        checkGmailStatus();
    } catch (error) {
        console.error('Error disconnecting Gmail:', error);
    }
}

// Track selected staged images
let selectedStagedImages = new Set();

async function scanEmails() {
    const daysBack = document.getElementById('days-back').value;
    const includeSeen = document.getElementById('include-seen').checked;
    const loadingDiv = document.getElementById('scan-loading');
    const resultsDiv = document.getElementById('scan-results');
    const summaryP = document.getElementById('scan-summary');

    loadingDiv.classList.remove('hidden');
    resultsDiv.classList.add('hidden');

    try {
        const response = await fetch(`${API_BASE}/api/gmail/scan?days=${daysBack}&include_seen=${includeSeen}`, {
            method: 'POST'
        });
        const data = await response.json();

        loadingDiv.classList.add('hidden');

        if (!response.ok) {
            alert(`Error: ${data.detail || 'Failed to scan emails'}`);
            return;
        }

        resultsDiv.classList.remove('hidden');
        summaryP.textContent = `Scan complete! Processed ${data.emails_processed} emails, found ${data.images_staged} new images.`;

        // Refresh retailer stats and staged images
        loadRetailerStats();
        loadStagedImages();

    } catch (error) {
        console.error('Error scanning emails:', error);
        loadingDiv.classList.add('hidden');
        alert(`Error: ${error.message}`);
    }
}

async function scanSelfEmails() {
    const fromEmail = document.getElementById('self-email').value.trim();
    const includeSeen = document.getElementById('include-seen').checked;
    const loadingDiv = document.getElementById('scan-loading');
    const resultsDiv = document.getElementById('scan-results');
    const summaryP = document.getElementById('scan-summary');

    if (!fromEmail) {
        alert('Please enter your email address');
        return;
    }

    loadingDiv.classList.remove('hidden');
    resultsDiv.classList.add('hidden');

    try {
        const response = await fetch(`${API_BASE}/api/gmail/scan-self?from_email=${encodeURIComponent(fromEmail)}&days=10&include_seen=${includeSeen}`, {
            method: 'POST'
        });
        const data = await response.json();

        loadingDiv.classList.add('hidden');

        if (!response.ok) {
            alert(`Error: ${data.detail || 'Failed to scan self-emails'}`);
            return;
        }

        resultsDiv.classList.remove('hidden');
        summaryP.textContent = `Self-email scan complete! Processed ${data.emails_processed} emails, found ${data.images_staged} new images.`;

        // Refresh retailer stats and staged images
        loadRetailerStats();
        loadStagedImages();

    } catch (error) {
        console.error('Error scanning self-emails:', error);
        loadingDiv.classList.add('hidden');
        alert(`Error: ${error.message}`);
    }
}

// Current retailer filter
let currentRetailerFilter = '';
let currentDateRangeFilter = '';

async function loadRetailerStats() {
    const container = document.getElementById('retailer-list');
    const filterSelect = document.getElementById('retailer-filter');

    try {
        const response = await fetch(`${API_BASE}/api/gmail/staged/retailers?status=pending`);
        const data = await response.json();

        if (data.retailers.length === 0) {
            container.innerHTML = '<p class="empty-state">No retailers found</p>';
            return;
        }

        // Build retailer chips
        container.innerHTML = data.retailers.map(r => `
            <div class="retailer-chip ${currentRetailerFilter === r.name ? 'selected' : ''}"
                 onclick="filterByRetailer('${r.name.replace(/'/g, "\\'")}')">
                <span class="name">${r.name}</span>
                <span class="count">${r.count}</span>
                <button class="reject-btn" onclick="event.stopPropagation(); rejectRetailer('${r.name.replace(/'/g, "\\'")}')">
                    Reject All
                </button>
            </div>
        `).join('');

        // Update filter dropdown
        filterSelect.innerHTML = '<option value="">All Retailers (' + data.total + ')</option>' +
            data.retailers.map(r => `<option value="${r.name}" ${currentRetailerFilter === r.name ? 'selected' : ''}>${r.name} (${r.count})</option>`).join('');

    } catch (error) {
        console.error('Error loading retailer stats:', error);
    }
}

async function rejectRetailer(retailer) {
    if (!confirm(`Reject ALL pending images from "${retailer}"?`)) return;

    try {
        const response = await fetch(`${API_BASE}/api/gmail/staged/reject-retailer?retailer=${encodeURIComponent(retailer)}`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('Failed to reject retailer images');
        }

        const data = await response.json();
        alert(`Rejected ${data.rejected} images from ${retailer}`);

        // Refresh both retailer stats and images
        loadRetailerStats();
        loadStagedImages();
    } catch (error) {
        console.error('Error rejecting retailer:', error);
        alert(`Error: ${error.message}`);
    }
}

function filterByRetailer(retailer) {
    if (currentRetailerFilter === retailer) {
        currentRetailerFilter = '';  // Toggle off
    } else {
        currentRetailerFilter = retailer;
    }
    document.getElementById('retailer-filter').value = currentRetailerFilter;
    loadRetailerStats();
    loadStagedImages();
}

function onRetailerFilterChange() {
    currentRetailerFilter = document.getElementById('retailer-filter').value;
    loadRetailerStats();
    loadStagedImages();
}

function onDateRangeFilterChange() {
    currentDateRangeFilter = document.getElementById('date-range-filter').value;
    loadStagedImages();
}

async function resetDateRange() {
    const dateRange = document.getElementById('date-range-filter').value;
    if (!dateRange) {
        alert('Please select a date range first (e.g., "4-5 years ago")');
        return;
    }

    const rangeLabel = document.querySelector(`#date-range-filter option[value="${dateRange}"]`).textContent;
    if (!confirm(`This will delete all staged images from "${rangeLabel}" and clear their processed email records so they can be rescanned.\n\nAfter this, run a scan with the appropriate date range to fetch those emails again.\n\nContinue?`)) {
        return;
    }

    const btn = document.getElementById('reset-date-range-btn');
    const originalText = btn.textContent;
    btn.textContent = 'Resetting...';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/api/gmail/staged/reset-by-date?date_range=${dateRange}`, {
            method: 'POST'
        });
        const data = await response.json();

        alert(`Reset complete!\n- Deleted ${data.staged_deleted} staged images\n- Cleared ${data.processed_cleared} processed email records\n\nNow run a scan with the appropriate date range to re-fetch those emails.`);

        loadRetailerStats();
        loadStagedImages();
    } catch (error) {
        console.error('Error resetting date range:', error);
        alert('Error resetting. See console for details.');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function cleanupBrokenImages() {
    if (!confirm('This will check all pending images and remove any with broken/expired URLs. Continue?')) {
        return;
    }

    const btn = document.getElementById('cleanup-broken-btn');
    const originalText = btn.textContent;
    btn.textContent = 'Checking...';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/api/gmail/staged/cleanup-broken`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.broken > 0) {
            alert(`Found and removed ${data.broken} broken images out of ${data.checked} checked.`);
        } else {
            alert(`Checked ${data.checked} images - all URLs are still valid.`);
        }

        loadRetailerStats();
        loadStagedImages();
    } catch (error) {
        console.error('Error checking broken images:', error);
        alert('Error checking images. See console for details.');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function loadStagedImages() {
    const container = document.getElementById('staged-images');
    const emptyState = document.getElementById('staged-empty');
    const countSpan = document.getElementById('staged-count');

    try {
        let url = `${API_BASE}/api/gmail/staged?status=pending&limit=200`;
        if (currentRetailerFilter) {
            url += `&retailer=${encodeURIComponent(currentRetailerFilter)}`;
        }
        if (currentDateRangeFilter) {
            url += `&date_range=${encodeURIComponent(currentDateRangeFilter)}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        countSpan.textContent = data.total;

        if (data.images.length === 0) {
            container.innerHTML = '';
            emptyState.classList.remove('hidden');
            return;
        }

        emptyState.classList.add('hidden');
        container.innerHTML = data.images.map(img => `
            <div class="staged-image-card" data-id="${img.id}" onclick="toggleStagedImage(${img.id}, this)">
                <img src="${img.image_url}" alt="${img.alt_text || 'Product'}" onerror="this.parentElement.style.display='none'">
                <button class="add-btn" onclick="event.stopPropagation(); importStagedImage(${img.id}, this)">
                    Add to Closet
                </button>
                <div class="staged-image-info">
                    <div class="retailer">${img.retailer}</div>
                    <div class="date">${img.email_date ? img.email_date.split(' ').slice(0, 4).join(' ') : ''}</div>
                </div>
            </div>
        `).join('');

        selectedStagedImages.clear();
        updateRejectButton();

    } catch (error) {
        console.error('Error loading staged images:', error);
    }
}

function selectAllStagedImages() {
    const cards = document.querySelectorAll('.staged-image-card');
    const allSelected = selectedStagedImages.size === cards.length;

    if (allSelected) {
        // Deselect all
        selectedStagedImages.clear();
        cards.forEach(card => card.classList.remove('selected'));
        document.getElementById('select-all-btn').textContent = 'Select All';
    } else {
        // Select all
        cards.forEach(card => {
            const id = parseInt(card.dataset.id);
            selectedStagedImages.add(id);
            card.classList.add('selected');
        });
        document.getElementById('select-all-btn').textContent = 'Deselect All';
    }
    updateRejectButton();
}

function toggleStagedImage(id, element) {
    if (selectedStagedImages.has(id)) {
        selectedStagedImages.delete(id);
        element.classList.remove('selected');
    } else {
        selectedStagedImages.add(id);
        element.classList.add('selected');
    }
    updateRejectButton();
}

function updateRejectButton() {
    const btn = document.getElementById('reject-selected-btn');
    btn.disabled = selectedStagedImages.size === 0;
    btn.textContent = selectedStagedImages.size > 0
        ? `Reject Selected (${selectedStagedImages.size})`
        : 'Reject Selected';
}

async function rejectSelectedImages() {
    if (selectedStagedImages.size === 0) return;

    if (!confirm(`Reject ${selectedStagedImages.size} selected images?`)) return;

    try {
        const response = await fetch(`${API_BASE}/api/gmail/staged/action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image_ids: Array.from(selectedStagedImages),
                action: 'reject'
            })
        });

        if (!response.ok) {
            throw new Error('Failed to reject images');
        }

        loadRetailerStats();
        loadStagedImages();
    } catch (error) {
        console.error('Error rejecting images:', error);
        alert(`Error: ${error.message}`);
    }
}

async function rejectAllPending() {
    const countSpan = document.getElementById('staged-count');
    const count = parseInt(countSpan.textContent) || 0;

    if (count === 0) {
        alert('No pending images to reject.');
        return;
    }

    if (!confirm(`Reject ALL ${count} remaining pending images? This cannot be undone.`)) return;

    try {
        const response = await fetch(`${API_BASE}/api/gmail/staged/reject-all`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('Failed to reject all images');
        }

        const data = await response.json();
        alert(`Rejected ${data.rejected} images. You're all done!`);

        loadRetailerStats();
        loadStagedImages();
    } catch (error) {
        console.error('Error rejecting all images:', error);
        alert(`Error: ${error.message}`);
    }
}

async function clearAllStagedImages() {
    if (!confirm('Clear ALL staged images and reset email history? This will allow a complete rescan of all your emails.')) return;

    try {
        const response = await fetch(`${API_BASE}/api/gmail/staged/clear?status=all&clear_processed=true`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to clear images');
        }

        const data = await response.json();
        alert(`Cleared ${data.deleted} images and ${data.processed_cleared} processed emails. You can now do a full rescan.`);
        loadStagedImages();
    } catch (error) {
        console.error('Error clearing images:', error);
        alert(`Error: ${error.message}`);
    }
}

async function importStagedImage(imageId, buttonElement) {
    buttonElement.disabled = true;
    buttonElement.textContent = 'Adding...';

    try {
        const response = await fetch(`${API_BASE}/api/gmail/staged/${imageId}/import`, {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Import failed');
        }

        buttonElement.textContent = 'Added!';
        buttonElement.classList.add('added');

        // Remove from grid after short delay
        setTimeout(() => {
            const card = buttonElement.closest('.staged-image-card');
            if (card) card.remove();

            // Check if empty
            const container = document.getElementById('staged-images');
            if (container.children.length === 0) {
                document.getElementById('staged-empty').classList.remove('hidden');
            }
        }, 1000);

    } catch (error) {
        console.error('Error importing image:', error);
        buttonElement.textContent = 'Failed';
        buttonElement.disabled = false;
        alert(`Import failed: ${error.message}`);
    }
}

async function importFromEmail(encodedUrl, encodedAlt, buttonElement) {
    const url = decodeURIComponent(encodedUrl);
    const alt = decodeURIComponent(encodedAlt);

    buttonElement.disabled = true;
    buttonElement.textContent = 'Importing...';
    buttonElement.classList.add('importing');

    try {
        const response = await fetch(`${API_BASE}/api/gmail/import`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image_url: url,
                suggested_name: alt || null
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Import failed');
        }

        const data = await response.json();
        buttonElement.textContent = 'Added!';
        buttonElement.classList.remove('importing');

    } catch (error) {
        console.error('Error importing item:', error);
        buttonElement.textContent = 'Failed';
        buttonElement.disabled = false;
        buttonElement.classList.remove('importing');
        alert(`Import failed: ${error.message}`);
    }
}

// Initialize Gmail section when switching to import tab
function initGmailSection() {
    const connectBtn = document.getElementById('connect-gmail-btn');
    const disconnectBtn = document.getElementById('disconnect-gmail-btn');
    const scanBtn = document.getElementById('scan-emails-btn');
    const refreshBtn = document.getElementById('refresh-staged-btn');
    const rejectBtn = document.getElementById('reject-selected-btn');
    const selectAllBtn = document.getElementById('select-all-btn');
    const clearAllBtn = document.getElementById('clear-all-btn');
    const rejectAllPendingBtn = document.getElementById('reject-all-pending-btn');

    if (connectBtn) {
        connectBtn.addEventListener('click', connectGmail);
    }
    if (disconnectBtn) {
        disconnectBtn.addEventListener('click', disconnectGmail);
    }
    if (scanBtn) {
        scanBtn.addEventListener('click', scanEmails);
    }
    const scanSelfBtn = document.getElementById('scan-self-btn');
    if (scanSelfBtn) {
        scanSelfBtn.addEventListener('click', scanSelfEmails);
    }
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            toggleDropdown(false);
            loadStagedImages();
        });
    }
    if (rejectBtn) {
        rejectBtn.addEventListener('click', rejectSelectedImages);
    }
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', selectAllStagedImages);
    }
    if (clearAllBtn) {
        clearAllBtn.addEventListener('click', () => {
            toggleDropdown(false);
            clearAllStagedImages();
        });
    }
    if (rejectAllPendingBtn) {
        rejectAllPendingBtn.addEventListener('click', () => {
            toggleDropdown(false);
            rejectAllPending();
        });
    }

    // Reset date range button
    const resetDateRangeBtn = document.getElementById('reset-date-range-btn');
    if (resetDateRangeBtn) {
        resetDateRangeBtn.addEventListener('click', () => {
            toggleDropdown(false);
            resetDateRange();
        });
    }

    // More Actions dropdown
    const moreActionsBtn = document.getElementById('more-actions-btn');
    const moreActionsMenu = document.getElementById('more-actions-menu');
    if (moreActionsBtn && moreActionsMenu) {
        moreActionsBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleDropdown();
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', () => {
            toggleDropdown(false);
        });

        // Prevent clicks inside dropdown from closing it immediately
        moreActionsMenu.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }

    // Check for OAuth callback params
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('gmail_connected')) {
        // Successfully connected - switch to import tab
        switchTab('import');
        window.history.replaceState({}, '', '/');
    } else if (urlParams.has('gmail_error')) {
        alert(`Gmail connection failed: ${urlParams.get('gmail_error')}`);
        window.history.replaceState({}, '', '/');
    }

    // Retailer filter dropdown
    const retailerFilter = document.getElementById('retailer-filter');
    if (retailerFilter) {
        retailerFilter.addEventListener('change', onRetailerFilterChange);
    }

    // Date range filter dropdown
    const dateRangeFilter = document.getElementById('date-range-filter');
    if (dateRangeFilter) {
        dateRangeFilter.addEventListener('change', onDateRangeFilterChange);
    }

    // Cleanup broken images button
    const cleanupBtn = document.getElementById('cleanup-broken-btn');
    if (cleanupBtn) {
        cleanupBtn.addEventListener('click', () => {
            toggleDropdown(false);
            cleanupBrokenImages();
        });
    }

    checkGmailStatus();
    loadRetailerStats();
    loadStagedImages();
}

// ============ Chat Functions ============

let currentChatId = null;
let chatList = [];

function initChat() {
    const chatForm = document.getElementById('chat-form');
    const newChatBtn = document.getElementById('new-chat-btn');
    const chatInput = document.getElementById('chat-input');

    if (chatForm) {
        chatForm.addEventListener('submit', handleChatSubmit);
    }

    if (newChatBtn) {
        newChatBtn.addEventListener('click', startNewChat);
    }

    // Auto-resize textarea
    if (chatInput) {
        chatInput.addEventListener('input', () => {
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
        });

        // Submit on Enter (without Shift)
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
    }

    loadChatList();
}

async function loadChatList() {
    try {
        const response = await fetch(`${API_BASE}/api/chat`);
        chatList = await response.json();
        renderChatList();
    } catch (error) {
        console.error('Error loading chat list:', error);
    }
}

function renderChatList() {
    const container = document.getElementById('chat-list');
    if (!container) return;

    if (chatList.length === 0) {
        container.innerHTML = '<p class="empty-state" style="padding: 20px; font-size: 0.85rem;">No conversations yet</p>';
        return;
    }

    container.innerHTML = chatList.map(chat => `
        <div class="chat-list-item ${chat.id === currentChatId ? 'active' : ''}" onclick="loadChat(${chat.id})">
            <div class="chat-list-item-title">${chat.title || 'Outfit Chat'}</div>
            <div class="chat-list-item-date">${formatDate(chat.created_at)}</div>
        </div>
    `).join('');
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
}

async function loadChat(chatId) {
    try {
        const response = await fetch(`${API_BASE}/api/chat/${chatId}`);
        if (!response.ok) throw new Error('Chat not found');

        const chat = await response.json();
        currentChatId = chatId;
        renderChat(chat);
        renderChatList();

        // Update location input if chat has one
        const locationInput = document.getElementById('chat-location');
        if (locationInput && chat.location) {
            locationInput.value = chat.location;
        }
    } catch (error) {
        console.error('Error loading chat:', error);
    }
}

function renderChat(chat) {
    const messagesContainer = document.getElementById('chat-messages');
    const header = document.getElementById('chat-header');

    if (header) {
        header.innerHTML = `
            <h2>${chat.title || 'Outfit Chat'}</h2>
            <p class="chat-subtitle">${chat.event_type ? `For ${chat.event_type}` : 'Your personal stylist'}</p>
        `;
    }

    if (!messagesContainer) return;

    messagesContainer.innerHTML = chat.messages.map(msg => renderChatMessage(msg)).join('');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function renderChatMessage(message) {
    const isUser = message.role === 'user';

    let outfitCardsHtml = '';
    if (message.outfit_data && message.outfit_data.length > 0) {
        outfitCardsHtml = message.outfit_data.map(outfit => `
            <div class="chat-outfit-card">
                <div class="chat-outfit-name">${outfit.outfit_name}</div>
                <div class="chat-outfit-items">
                    ${outfit.items.map(item => `
                        <div class="chat-outfit-item" onclick="showItemDetails(${item.id})">
                            <img src="${item.image_path || ''}" alt="${item.name}"
                                 onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2280%22 height=%2280%22><rect fill=%22%23e1e8ed%22 width=%2280%22 height=%2280%22/></svg>'">
                            <div class="chat-outfit-item-name">${item.name}</div>
                        </div>
                    `).join('')}
                </div>
                ${outfit.reasoning ? `<div class="chat-outfit-reasoning">${outfit.reasoning}</div>` : ''}
            </div>
        `).join('');
    }

    return `
        <div class="chat-message ${isUser ? 'user' : 'assistant'}">
            <div class="chat-message-avatar">${isUser ? 'U' : 'AI'}</div>
            <div class="chat-message-content">
                <div class="chat-message-bubble">${escapeHtml(message.content)}</div>
                ${outfitCardsHtml}
            </div>
        </div>
    `;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function startNewChat() {
    currentChatId = null;
    const messagesContainer = document.getElementById('chat-messages');
    const header = document.getElementById('chat-header');
    const locationInput = document.getElementById('chat-location');

    if (header) {
        header.innerHTML = `
            <h2>Outfit Assistant</h2>
            <p class="chat-subtitle">Ask me to put together an outfit for you!</p>
        `;
    }

    if (messagesContainer) {
        messagesContainer.innerHTML = `
            <div class="chat-welcome">
                <h3>Hi! I'm your personal stylist.</h3>
                <p>Tell me what you need an outfit for, and I'll help you put something together from your wardrobe.</p>
                <div class="quick-starts">
                    <button class="quick-start-btn" onclick="startQuickChat('casual')">Casual day out</button>
                    <button class="quick-start-btn" onclick="startQuickChat('work')">Work outfit</button>
                    <button class="quick-start-btn" onclick="startQuickChat('date')">Date night</button>
                    <button class="quick-start-btn" onclick="startQuickChat('party')">Going to a party</button>
                </div>
            </div>
        `;
    }

    if (locationInput) {
        locationInput.value = '';
    }

    renderChatList();
}

function startQuickChat(eventType) {
    const messages = {
        'casual': "Put together a casual outfit for me for a day out",
        'work': "I need a professional outfit for work today",
        'date': "Help me pick out something nice for a date night",
        'party': "I'm going to a party tonight, what should I wear?"
    };

    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.value = messages[eventType] || `Put together a ${eventType} outfit for me`;
        handleChatSubmit(new Event('submit'));
    }
}

async function handleChatSubmit(e) {
    e.preventDefault();

    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('chat-send-btn');
    const messagesContainer = document.getElementById('chat-messages');
    const locationInput = document.getElementById('chat-location');

    const message = chatInput.value.trim();
    if (!message) return;

    // Clear input
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Disable send button
    sendBtn.disabled = true;

    // If this is a new chat, create it
    if (!currentChatId) {
        // Clear welcome message
        messagesContainer.innerHTML = '';

        // Add user message to UI
        messagesContainer.innerHTML += renderChatMessage({
            role: 'user',
            content: message
        });

        // Add typing indicator
        messagesContainer.innerHTML += `
            <div class="chat-message assistant" id="typing-indicator">
                <div class="chat-message-avatar">AI</div>
                <div class="chat-message-content">
                    <div class="chat-typing">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            </div>
        `;
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        try {
            // Detect event type from message
            const eventType = detectEventType(message);

            const response = await fetch(`${API_BASE}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    event_type: eventType,
                    location: locationInput?.value || null,
                    initial_message: message
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to create chat');
            }

            const chat = await response.json();
            currentChatId = chat.id;
            renderChat(chat);
            loadChatList();

        } catch (error) {
            console.error('Error creating chat:', error);
            // Remove typing indicator and show error
            document.getElementById('typing-indicator')?.remove();
            messagesContainer.innerHTML += renderChatMessage({
                role: 'assistant',
                content: `Sorry, I had trouble with that. ${error.message}`
            });
        }

    } else {
        // Continue existing chat
        messagesContainer.innerHTML += renderChatMessage({
            role: 'user',
            content: message
        });

        // Add typing indicator
        messagesContainer.innerHTML += `
            <div class="chat-message assistant" id="typing-indicator">
                <div class="chat-message-avatar">AI</div>
                <div class="chat-message-content">
                    <div class="chat-typing">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            </div>
        `;
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        try {
            const response = await fetch(`${API_BASE}/api/chat/${currentChatId}/message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: message
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to send message');
            }

            const chat = await response.json();
            renderChat(chat);

        } catch (error) {
            console.error('Error sending message:', error);
            document.getElementById('typing-indicator')?.remove();
            messagesContainer.innerHTML += renderChatMessage({
                role: 'assistant',
                content: `Sorry, I had trouble with that. ${error.message}`
            });
        }
    }

    sendBtn.disabled = false;
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function detectEventType(message) {
    const msg = message.toLowerCase();
    if (msg.includes('work') || msg.includes('office') || msg.includes('professional') || msg.includes('meeting')) {
        return 'work';
    }
    if (msg.includes('date') || msg.includes('romantic') || msg.includes('dinner')) {
        return 'date';
    }
    if (msg.includes('party') || msg.includes('club') || msg.includes('night out')) {
        return 'party';
    }
    if (msg.includes('formal') || msg.includes('wedding') || msg.includes('event')) {
        return 'formal';
    }
    if (msg.includes('workout') || msg.includes('gym') || msg.includes('exercise')) {
        return 'workout';
    }
    if (msg.includes('beach') || msg.includes('pool') || msg.includes('swim')) {
        return 'beach';
    }
    if (msg.includes('outdoor') || msg.includes('hike') || msg.includes('walk')) {
        return 'outdoor';
    }
    return 'casual';
}

// Initialize chat when switching to recommend tab
const originalSwitchTab = switchTab;
switchTab = function(tabId) {
    originalSwitchTab(tabId);
    if (tabId === 'recommend') {
        initChat();
    }
};

// Make chat functions globally available
window.loadChat = loadChat;
window.startQuickChat = startQuickChat;

// ============ Item Edit Functions ============

let currentEditItem = null;

async function showItemDetails(itemId) {
    // Fetch full item details including notes
    try {
        const [itemResponse, notesResponse] = await Promise.all([
            fetch(`${API_BASE}/api/clothes/${itemId}`),
            fetch(`${API_BASE}/api/chat/items/${itemId}/notes`)
        ]);

        const item = await itemResponse.json();
        const notes = await notesResponse.json();

        currentEditItem = item;
        renderItemModalWithEdit(item, notes);
    } catch (error) {
        console.error('Error fetching item details:', error);
        // Fallback to basic modal
        const item = wardrobeItems.find(i => i.id === itemId);
        if (item) {
            renderItemModalWithEdit(item, []);
        }
    }
}

function renderItemModalWithEdit(item, notes) {
    const weatherOptions = ['hot', 'warm', 'mild', 'cool', 'cold', 'rainy'];
    const occasionOptions = ['casual', 'work', 'formal', 'party', 'date', 'workout', 'outdoor', 'beach', 'wedding'];
    const styleOptions = ['casual', 'formal', 'business casual', 'sporty', 'bohemian', 'elegant', 'streetwear', 'preppy', 'minimalist'];

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

        <!-- Notes Section -->
        <div class="item-notes-section">
            <h4>Notes & Feedback</h4>
            <div class="item-notes-list" id="item-notes-list">
                ${notes.length === 0 ? '<p style="color: var(--text-secondary); font-size: 0.9rem;">No notes yet</p>' :
                    notes.map(note => `
                        <div class="item-note">
                            <div class="item-note-content">
                                <div class="item-note-text">${escapeHtml(note.note)}</div>
                                <div class="item-note-meta">${note.note_type || 'general'} • ${note.source === 'chat' ? 'from chat' : 'manual'}</div>
                            </div>
                            <button class="item-note-delete" onclick="deleteItemNote(${note.id})">&times;</button>
                        </div>
                    `).join('')
                }
            </div>
            <div class="add-note-form">
                <input type="text" id="new-note-input" placeholder="Add a note about this item...">
                <select id="new-note-type">
                    <option value="general">General</option>
                    <option value="weather">Weather</option>
                    <option value="occasion">Occasion</option>
                    <option value="style">Style</option>
                    <option value="fit">Fit</option>
                </select>
                <button class="btn btn-small btn-primary" onclick="addItemNote(${item.id})">Add</button>
            </div>
        </div>

        <!-- Edit Section -->
        <div class="item-edit-form">
            <h4>Edit Item</h4>
            <div class="edit-form-grid">
                <div class="edit-field">
                    <label>Name</label>
                    <input type="text" id="edit-name" value="${item.name || ''}">
                </div>
                <div class="edit-field">
                    <label>Color</label>
                    <input type="text" id="edit-color" value="${item.color || ''}">
                </div>
                <div class="edit-field">
                    <label>Material</label>
                    <input type="text" id="edit-material" value="${item.material || ''}">
                </div>
                <div class="edit-field">
                    <label>Pattern</label>
                    <input type="text" id="edit-pattern" value="${item.pattern || ''}">
                </div>
                <div class="edit-field">
                    <label>Style</label>
                    <select id="edit-style">
                        ${styleOptions.map(s => `<option value="${s}" ${item.style === s ? 'selected' : ''}>${s}</option>`).join('')}
                    </select>
                </div>
                <div class="edit-field">
                    <label>Category</label>
                    <select id="edit-category">
                        <option value="top" ${item.category === 'top' ? 'selected' : ''}>Top</option>
                        <option value="bottom" ${item.category === 'bottom' ? 'selected' : ''}>Bottom</option>
                        <option value="dress" ${item.category === 'dress' ? 'selected' : ''}>Dress</option>
                        <option value="outerwear" ${item.category === 'outerwear' ? 'selected' : ''}>Outerwear</option>
                        <option value="shoes" ${item.category === 'shoes' ? 'selected' : ''}>Shoes</option>
                        <option value="accessory" ${item.category === 'accessory' ? 'selected' : ''}>Accessory</option>
                        <option value="activewear" ${item.category === 'activewear' ? 'selected' : ''}>Activewear</option>
                    </select>
                </div>
                <div class="multi-select-field">
                    <label>Weather Suitability</label>
                    <div class="multi-select-options" id="edit-weather">
                        ${weatherOptions.map(w => `
                            <span class="multi-select-option ${(item.weather_suitability || []).includes(w) ? 'selected' : ''}"
                                  onclick="toggleMultiSelect(this, 'weather')"
                                  data-value="${w}">${w}</span>
                        `).join('')}
                    </div>
                </div>
                <div class="multi-select-field">
                    <label>Occasion Suitability</label>
                    <div class="multi-select-options" id="edit-occasion">
                        ${occasionOptions.map(o => `
                            <span class="multi-select-option ${(item.occasion_suitability || []).includes(o) ? 'selected' : ''}"
                                  onclick="toggleMultiSelect(this, 'occasion')"
                                  data-value="${o}">${o}</span>
                        `).join('')}
                    </div>
                </div>
            </div>
            <div class="edit-actions">
                <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="saveItemChanges(${item.id})">Save Changes</button>
            </div>
        </div>

        <div class="modal-actions" style="margin-top: 20px; border-top: 1px solid var(--border-color); padding-top: 20px;">
            <button class="btn btn-danger" onclick="deleteItem(${item.id})">Delete Item</button>
        </div>
    `;
    itemModal.classList.remove('hidden');
}

function toggleMultiSelect(element, type) {
    element.classList.toggle('selected');
}

function getMultiSelectValues(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return [];

    const selected = container.querySelectorAll('.multi-select-option.selected');
    return Array.from(selected).map(el => el.dataset.value);
}

async function saveItemChanges(itemId) {
    const updateData = {
        name: document.getElementById('edit-name').value,
        color: document.getElementById('edit-color').value,
        material: document.getElementById('edit-material').value,
        pattern: document.getElementById('edit-pattern').value,
        style: document.getElementById('edit-style').value,
        category: document.getElementById('edit-category').value,
        weather_suitability: getMultiSelectValues('edit-weather'),
        occasion_suitability: getMultiSelectValues('edit-occasion'),
    };

    try {
        const response = await fetch(`${API_BASE}/api/clothes/${itemId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updateData)
        });

        if (!response.ok) {
            throw new Error('Failed to update item');
        }

        const updatedItem = await response.json();

        // Refresh wardrobe
        loadWardrobe();

        // Refresh the modal with updated data
        const notesResponse = await fetch(`${API_BASE}/api/chat/items/${itemId}/notes`);
        const notes = await notesResponse.json();
        renderItemModalWithEdit(updatedItem, notes);

        alert('Item updated successfully!');

    } catch (error) {
        console.error('Error saving item changes:', error);
        alert(`Error: ${error.message}`);
    }
}

async function addItemNote(itemId) {
    const noteInput = document.getElementById('new-note-input');
    const noteType = document.getElementById('new-note-type');

    const note = noteInput.value.trim();
    if (!note) {
        alert('Please enter a note');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/chat/items/${itemId}/notes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                note: note,
                note_type: noteType.value
            })
        });

        if (!response.ok) {
            throw new Error('Failed to add note');
        }

        // Refresh the modal
        noteInput.value = '';
        showItemDetails(itemId);

    } catch (error) {
        console.error('Error adding note:', error);
        alert(`Error: ${error.message}`);
    }
}

async function deleteItemNote(noteId) {
    if (!confirm('Delete this note?')) return;

    try {
        const response = await fetch(`${API_BASE}/api/chat/items/notes/${noteId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to delete note');
        }

        // Refresh modal
        if (currentEditItem) {
            showItemDetails(currentEditItem.id);
        }

    } catch (error) {
        console.error('Error deleting note:', error);
        alert(`Error: ${error.message}`);
    }
}

// Make edit functions globally available
window.toggleMultiSelect = toggleMultiSelect;
window.saveItemChanges = saveItemChanges;
window.addItemNote = addItemNote;
window.deleteItemNote = deleteItemNote;

// ============ Outfit Builder Functions ============

let savedOutfits = [];
let currentOutfitId = null;
let currentOutfitItems = [];  // Array of item IDs in the current outfit
let outfitWardrobeItems = []; // Copy of wardrobe items for the picker

function initOutfitBuilder() {
    const newOutfitBtn = document.getElementById('new-outfit-btn');
    const backBtn = document.getElementById('back-to-outfits-btn');
    const saveBtn = document.getElementById('save-outfit-btn');
    const deleteBtn = document.getElementById('delete-outfit-btn');
    const categoryFilter = document.getElementById('outfit-category-filter');
    const dropZone = document.getElementById('outfit-drop-zone');

    if (newOutfitBtn) {
        newOutfitBtn.addEventListener('click', showOutfitEditor);
    }

    if (backBtn) {
        backBtn.addEventListener('click', hideOutfitEditor);
    }

    if (saveBtn) {
        saveBtn.addEventListener('click', saveOutfit);
    }

    if (deleteBtn) {
        deleteBtn.addEventListener('click', deleteCurrentOutfit);
    }

    if (categoryFilter) {
        categoryFilter.addEventListener('change', (e) => {
            renderOutfitWardrobePicker(e.target.value);
        });
    }

    // Setup drag and drop for the drop zone
    if (dropZone) {
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            const itemId = parseInt(e.dataTransfer.getData('text/plain'));
            if (itemId && !currentOutfitItems.includes(itemId)) {
                addItemToOutfit(itemId);
            }
        });
    }

    loadSavedOutfits();
}

async function loadSavedOutfits() {
    try {
        const response = await fetch(`${API_BASE}/api/outfits`);
        savedOutfits = await response.json();
        renderSavedOutfitsList();
    } catch (error) {
        console.error('Error loading saved outfits:', error);
    }
}

function renderSavedOutfitsList() {
    const container = document.getElementById('saved-outfits-list');
    if (!container) return;

    if (savedOutfits.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No outfits saved yet.</p>
                <p>Create your first outfit!</p>
            </div>
        `;
        return;
    }

    container.innerHTML = savedOutfits.map(outfit => `
        <div class="saved-outfit-card" onclick="editOutfit(${outfit.id})">
            <div class="saved-outfit-card-name">${outfit.name}</div>
            <div class="saved-outfit-card-meta">${outfit.item_count} items</div>
            <div class="saved-outfit-preview">
                ${outfit.preview_images.slice(0, 4).map(img => `
                    <img src="${img}" alt="Preview" onerror="this.style.display='none'">
                `).join('')}
                ${outfit.item_count > 4 ? `<div class="saved-outfit-preview-more">+${outfit.item_count - 4}</div>` : ''}
            </div>
        </div>
    `).join('');
}

function showOutfitEditor() {
    const savedOutfitsSection = document.querySelector('.saved-outfits-section');
    const editor = document.getElementById('outfit-editor');
    const deleteBtn = document.getElementById('delete-outfit-btn');
    const nameInput = document.getElementById('outfit-name-input');
    const descriptionInput = document.getElementById('outfit-description');

    if (savedOutfitsSection) savedOutfitsSection.classList.add('hidden');
    if (editor) editor.classList.remove('hidden');
    if (deleteBtn) deleteBtn.classList.add('hidden');

    // Reset for new outfit
    currentOutfitId = null;
    currentOutfitItems = [];
    if (nameInput) nameInput.value = '';
    if (descriptionInput) descriptionInput.value = '';

    loadOutfitWardrobeItems();
    renderOutfitItems();
}

function hideOutfitEditor() {
    const savedOutfitsSection = document.querySelector('.saved-outfits-section');
    const editor = document.getElementById('outfit-editor');

    if (savedOutfitsSection) savedOutfitsSection.classList.remove('hidden');
    if (editor) editor.classList.add('hidden');

    loadSavedOutfits();
}

async function editOutfit(outfitId) {
    try {
        const response = await fetch(`${API_BASE}/api/outfits/${outfitId}`);
        if (!response.ok) throw new Error('Outfit not found');

        const outfit = await response.json();
        currentOutfitId = outfit.id;
        currentOutfitItems = outfit.item_ids || [];

        const nameInput = document.getElementById('outfit-name-input');
        const descriptionInput = document.getElementById('outfit-description');
        const deleteBtn = document.getElementById('delete-outfit-btn');

        if (nameInput) nameInput.value = outfit.name;
        if (descriptionInput) descriptionInput.value = outfit.description || '';
        if (deleteBtn) deleteBtn.classList.remove('hidden');

        const savedOutfitsSection = document.querySelector('.saved-outfits-section');
        const editor = document.getElementById('outfit-editor');

        if (savedOutfitsSection) savedOutfitsSection.classList.add('hidden');
        if (editor) editor.classList.remove('hidden');

        await loadOutfitWardrobeItems();
        renderOutfitItems();

    } catch (error) {
        console.error('Error loading outfit:', error);
        alert('Error loading outfit');
    }
}

async function loadOutfitWardrobeItems() {
    try {
        const response = await fetch(`${API_BASE}/api/clothes`);
        outfitWardrobeItems = await response.json();
        renderOutfitWardrobePicker('');
    } catch (error) {
        console.error('Error loading wardrobe items:', error);
    }
}

function renderOutfitWardrobePicker(category = '') {
    const container = document.getElementById('outfit-wardrobe-items');
    if (!container) return;

    let items = outfitWardrobeItems;
    if (category) {
        items = items.filter(item => item.category === category);
    }

    if (items.length === 0) {
        container.innerHTML = '<div class="empty-state" style="padding: 20px;">No items found</div>';
        return;
    }

    container.innerHTML = items.map(item => `
        <div class="outfit-wardrobe-item ${currentOutfitItems.includes(item.id) ? 'selected' : ''}"
             draggable="true"
             ondragstart="handleOutfitItemDragStart(event, ${item.id})"
             onclick="toggleOutfitItem(${item.id})">
            <img src="${item.image_path || ''}" alt="${item.name}"
                 onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2280%22 height=%2280%22><rect fill=%22%23e1e8ed%22 width=%2280%22 height=%2280%22/></svg>'">
            <div class="outfit-wardrobe-item-name">${item.name}</div>
        </div>
    `).join('');
}

function handleOutfitItemDragStart(event, itemId) {
    event.dataTransfer.setData('text/plain', itemId.toString());
}

function toggleOutfitItem(itemId) {
    if (currentOutfitItems.includes(itemId)) {
        removeItemFromOutfit(itemId);
    } else {
        addItemToOutfit(itemId);
    }
}

function addItemToOutfit(itemId) {
    if (!currentOutfitItems.includes(itemId)) {
        currentOutfitItems.push(itemId);
        renderOutfitItems();
        renderOutfitWardrobePicker(document.getElementById('outfit-category-filter')?.value || '');
    }
}

function removeItemFromOutfit(itemId) {
    currentOutfitItems = currentOutfitItems.filter(id => id !== itemId);
    renderOutfitItems();
    renderOutfitWardrobePicker(document.getElementById('outfit-category-filter')?.value || '');
}

function renderOutfitItems() {
    const container = document.getElementById('outfit-items');
    if (!container) return;

    if (currentOutfitItems.length === 0) {
        container.innerHTML = '<div class="outfit-items-empty">No items added yet</div>';
        return;
    }

    // Get the full item objects for the selected IDs
    const selectedItems = currentOutfitItems.map(id =>
        outfitWardrobeItems.find(item => item.id === id)
    ).filter(Boolean);

    container.innerHTML = selectedItems.map(item => `
        <div class="outfit-selected-item" draggable="true">
            <img src="${item.image_path || ''}" alt="${item.name}"
                 onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22><rect fill=%22%23e1e8ed%22 width=%22100%22 height=%22100%22/></svg>'">
            <div class="outfit-selected-item-name">${item.name}</div>
            <button class="remove-btn" onclick="removeItemFromOutfit(${item.id})">&times;</button>
        </div>
    `).join('');
}

async function saveOutfit() {
    const nameInput = document.getElementById('outfit-name-input');
    const descriptionInput = document.getElementById('outfit-description');

    const name = nameInput?.value.trim();
    if (!name) {
        alert('Please enter a name for this outfit');
        nameInput?.focus();
        return;
    }

    if (currentOutfitItems.length === 0) {
        alert('Please add at least one item to the outfit');
        return;
    }

    const outfitData = {
        name: name,
        description: descriptionInput?.value.trim() || null,
        item_ids: currentOutfitItems
    };

    try {
        let response;
        if (currentOutfitId) {
            // Update existing outfit
            response = await fetch(`${API_BASE}/api/outfits/${currentOutfitId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(outfitData)
            });
        } else {
            // Create new outfit
            response = await fetch(`${API_BASE}/api/outfits`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(outfitData)
            });
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save outfit');
        }

        alert(currentOutfitId ? 'Outfit updated!' : 'Outfit saved!');
        hideOutfitEditor();

    } catch (error) {
        console.error('Error saving outfit:', error);
        alert(`Error: ${error.message}`);
    }
}

async function deleteCurrentOutfit() {
    if (!currentOutfitId) return;

    if (!confirm('Are you sure you want to delete this outfit?')) return;

    try {
        const response = await fetch(`${API_BASE}/api/outfits/${currentOutfitId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to delete outfit');
        }

        alert('Outfit deleted');
        hideOutfitEditor();

    } catch (error) {
        console.error('Error deleting outfit:', error);
        alert(`Error: ${error.message}`);
    }
}

// Initialize outfit builder when switching to create-outfit tab
const originalSwitchTabForOutfit = switchTab;
switchTab = function(tabId) {
    originalSwitchTabForOutfit(tabId);
    if (tabId === 'create-outfit') {
        initOutfitBuilder();
    }
};

// Make outfit builder functions globally available
window.editOutfit = editOutfit;
window.toggleOutfitItem = toggleOutfitItem;
window.removeItemFromOutfit = removeItemFromOutfit;
window.handleOutfitItemDragStart = handleOutfitItemDragStart;
