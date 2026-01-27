// MyCloset Frontend Application

const API_BASE = '';

// State
let currentTab = 'wardrobe';
let wardrobeItems = [];

// DOM Elements - initialized in init()
let tabs, tabContents, wardrobeGrid, categoryFilter, recommendForm, addForm;
let itemPrompt, addBtn, addStatus;
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
    itemPrompt = document.getElementById('item-prompt');
    addBtn = document.getElementById('add-btn');
    addStatus = document.getElementById('add-status');
    itemModal = document.getElementById('item-modal');
    modalBody = document.getElementById('modal-body');
    modalClose = document.querySelector('.modal-close');

    // Check critical elements exist
    if (!itemPrompt || !addBtn || !addForm) {
        console.error('[MyCloset] Critical DOM elements not found!');
        return;
    }

    console.log('[MyCloset] DOM elements found, setting up...');

    initTabs();
    initCategoryFilter();
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

// Category Filter
function initCategoryFilter() {
    if (categoryFilter) {
        categoryFilter.addEventListener('change', (e) => {
            loadWardrobe(e.target.value);
        });
    }
}

// Forms
function initForms() {
    addForm.addEventListener('submit', handleAddItem);
    recommendForm.addEventListener('submit', handleGetRecommendations);
}

async function handleAddItem(e) {
    e.preventDefault();

    const prompt = itemPrompt.value.trim();
    if (!prompt) {
        alert('Please describe the clothing item');
        return;
    }

    addBtn.disabled = true;
    addBtn.textContent = 'Adding...';
    addStatus.classList.remove('hidden', 'success', 'error');
    addStatus.textContent = 'Analyzing your description...';

    try {
        const response = await fetch(`${API_BASE}/api/clothes/prompt`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ prompt })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Failed to add item');
        }

        const item = await response.json();

        addStatus.classList.add('success');
        addStatus.innerHTML = `
            <strong>Success!</strong> Added "${item.name}" to your wardrobe.<br>
            <small>Category: ${item.subcategory || item.category} | Style: ${item.style} | Color: ${item.color}</small>
        `;

        // Reset form
        setTimeout(() => {
            itemPrompt.value = '';
            addBtn.textContent = 'Add to Wardrobe';
            addBtn.disabled = false;
        }, 2000);

    } catch (error) {
        console.error('Error adding item:', error);
        addStatus.classList.add('error');
        addStatus.textContent = `Error: ${error.message}. Please try again.`;
        addBtn.disabled = false;
        addBtn.textContent = 'Add to Wardrobe';
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
