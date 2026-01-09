// Violations analytics page - displays violation statistics
// with views by date and facility type/region/gender.

let violationsData = null;
let currentGroupBy = 'facility_type'; // 'facility_type', 'region', 'gender'

// Load and display data
async function init() {
    try {
        const response = await fetch('/data/violations_data.json');
        if (!response.ok) {
            throw new Error(`Failed to load data: ${response.statusText}`);
        }
        
        violationsData = await response.json();
        
        hideLoading();
        showContent();
        renderSummaryStats();
        renderByYearChart();
        renderGroupedChart();
        setupGroupByDropdown();
        
    } catch (error) {
        console.error('Error loading data:', error);
        showError(`Failed to load violations data: ${error.message}`);
        hideLoading();
    }
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function showContent() {
    document.getElementById('content').style.display = 'block';
}

function showError(message) {
    const errorEl = document.getElementById('error');
    errorEl.textContent = message;
    errorEl.style.display = 'block';
}

function renderSummaryStats() {
    const container = document.getElementById('summaryStats');
    if (!container || !violationsData) return;
    
    // Calculate totals across all data
    let totalLow = 0, totalModerate = 0, totalSevere = 0, totalAll = 0;
    
    for (const item of violationsData.by_year) {
        totalLow += item.low || 0;
        totalModerate += item.moderate || 0;
        totalSevere += item.severe || 0;
        totalAll += item.total || 0;
    }
    
    container.innerHTML = `
        <div class="stat-card">
            <div class="stat-number">${totalAll}</div>
            <div class="stat-label">Total Substantiated Violations</div>
        </div>
        <div class="stat-card">
            <div class="stat-number stat-number-low">${totalLow}</div>
            <div class="stat-label">Low Severity</div>
        </div>
        <div class="stat-card">
            <div class="stat-number stat-number-moderate">${totalModerate}</div>
            <div class="stat-label">Moderate Severity</div>
        </div>
        <div class="stat-card">
            <div class="stat-number stat-number-severe">${totalSevere}</div>
            <div class="stat-label">Severe Severity</div>
        </div>
    `;
}

function renderStackedBarChart(containerId, data, labelKey, sortByTotal = true) {
    const container = document.getElementById(containerId);
    if (!container || !data || data.length === 0) {
        if (container) {
            container.innerHTML = '<div style="color: #666; font-size: 0.9em; font-style: italic; padding: 20px; text-align: center;">No data available</div>';
        }
        return;
    }
    
    // Sort data by total (descending) if requested, otherwise keep original order
    let sortedData = [...data];
    if (sortByTotal) {
        sortedData.sort((a, b) => (b.total || 0) - (a.total || 0));
    }
    
    // Find max total for scaling
    const maxTotal = Math.max(...sortedData.map(d => d.total || 0));
    
    const barsHtml = sortedData.map(item => {
        const total = item.total || 0;
        const low = item.low || 0;
        const moderate = item.moderate || 0;
        const severe = item.severe || 0;
        
        // Calculate percentages for stacked bar
        const lowPct = maxTotal > 0 ? (low / maxTotal) * 100 : 0;
        const moderatePct = maxTotal > 0 ? (moderate / maxTotal) * 100 : 0;
        const severePct = maxTotal > 0 ? (severe / maxTotal) * 100 : 0;
        
        const label = item[labelKey] || 'Unknown';
        
        return `
            <div class="bar-chart-row">
                <div class="bar-chart-label" title="${escapeHtml(label)}">${escapeHtml(label)}</div>
                <div class="bar-chart-bar-container" title="Low: ${low}, Moderate: ${moderate}, Severe: ${severe}">
                    <div class="bar-segment bar-segment-low" style="width: ${lowPct}%"></div>
                    <div class="bar-segment bar-segment-moderate" style="width: ${moderatePct}%"></div>
                    <div class="bar-segment bar-segment-severe" style="width: ${severePct}%"></div>
                </div>
                <div class="bar-chart-count">${total}</div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = barsHtml;
}

function renderByYearChart() {
    if (!violationsData || !violationsData.by_year) return;
    
    // Sort years chronologically (already sorted in data, but ensure order)
    const sortedData = [...violationsData.by_year].sort((a, b) => a.year.localeCompare(b.year));
    
    renderStackedBarChart('byYearChart', sortedData, 'year', false);
}

function renderGroupedChart() {
    const container = document.getElementById('byGroupedChart');
    if (!container) return;
    
    let data = [];
    let labelKey = '';
    
    if (currentGroupBy === 'facility_type') {
        data = violationsData.by_facility_type || [];
        labelKey = 'facility_type';
    } else if (currentGroupBy === 'region') {
        data = violationsData.by_region || [];
        labelKey = 'region';
    } else if (currentGroupBy === 'gender') {
        data = violationsData.by_gender || [];
        labelKey = 'gender';
    }
    
    if (!data || data.length === 0) {
        container.innerHTML = '<div style="color: #666; font-size: 0.9em; font-style: italic; padding: 20px; text-align: center;">No data available</div>';
        return;
    }
    
    renderStackedBarChart('byGroupedChart', data, labelKey, true);
}

function setupGroupByDropdown() {
    const dropdown = document.getElementById('groupBySelect');
    if (!dropdown) return;
    
    dropdown.addEventListener('change', (e) => {
        currentGroupBy = e.target.value;
        renderGroupedChart();
    });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize the page
init();
