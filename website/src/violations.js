// Violations analytics page - displays violation statistics
// with views by date and facility type/region/gender/capacity.

let violationsData = null;
let currentGroupBy = 'facility_type'; // 'facility_type', 'region', 'gender', 'capacity'
let capacityNormalized = false;

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
        setupCapacityNormalizedCheckbox();
        
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

function renderStackedBarChart(containerId, data, labelKey, sortByTotal = true, normalized = false) {
    const container = document.getElementById(containerId);
    if (!container || !data || data.length === 0) {
        if (container) {
            container.innerHTML = '<div style="color: #666; font-size: 0.9em; font-style: italic; padding: 20px; text-align: center;">No data available</div>';
        }
        return;
    }
    
    // Filter out items with no capacity if normalized mode is on
    let filteredData = [...data];
    if (normalized) {
        filteredData = filteredData.filter(d => d.capacity && d.capacity > 0);
        if (filteredData.length === 0) {
            container.innerHTML = '<div style="color: #666; font-size: 0.9em; font-style: italic; padding: 20px; text-align: center;">No data available with known capacity</div>';
            return;
        }
    }
    
    // Sort data by total (descending) if requested, otherwise keep original order
    let sortedData = [...filteredData];
    if (sortByTotal) {
        if (normalized) {
            // Sort by normalized value (total / capacity)
            sortedData.sort((a, b) => {
                const aVal = a.capacity > 0 ? a.total / a.capacity : 0;
                const bVal = b.capacity > 0 ? b.total / b.capacity : 0;
                return bVal - aVal;
            });
        } else {
            sortedData.sort((a, b) => (b.total || 0) - (a.total || 0));
        }
    }
    
    // Calculate max value for scaling
    let maxValue;
    if (normalized) {
        maxValue = Math.max(...sortedData.map(d => d.capacity > 0 ? d.total / d.capacity : 0));
    } else {
        maxValue = Math.max(...sortedData.map(d => d.total || 0));
    }
    
    const barsHtml = sortedData.map(item => {
        const total = item.total || 0;
        const low = item.low || 0;
        const moderate = item.moderate || 0;
        const severe = item.severe || 0;
        const capacity = item.capacity || 0;
        
        let displayValue, lowPct, moderatePct, severePct;
        
        if (normalized && capacity > 0) {
            // Normalized mode: divide by capacity
            const normalizedTotal = total / capacity;
            displayValue = normalizedTotal.toFixed(2);
            lowPct = maxValue > 0 ? ((low / capacity) / maxValue) * 100 : 0;
            moderatePct = maxValue > 0 ? ((moderate / capacity) / maxValue) * 100 : 0;
            severePct = maxValue > 0 ? ((severe / capacity) / maxValue) * 100 : 0;
        } else {
            displayValue = total.toString();
            lowPct = maxValue > 0 ? (low / maxValue) * 100 : 0;
            moderatePct = maxValue > 0 ? (moderate / maxValue) * 100 : 0;
            severePct = maxValue > 0 ? (severe / maxValue) * 100 : 0;
        }
        
        const label = item[labelKey] || 'Unknown';
        const tooltip = normalized && capacity > 0
            ? `Low: ${low}, Moderate: ${moderate}, Severe: ${severe} (Capacity: ${capacity})`
            : `Low: ${low}, Moderate: ${moderate}, Severe: ${severe}`;
        
        return `
            <div class="bar-chart-row">
                <div class="bar-chart-label" title="${escapeHtml(label)}">${escapeHtml(label)}</div>
                <div class="bar-chart-bar-container" title="${tooltip}">
                    <div class="bar-segment bar-segment-low" style="width: ${lowPct}%"></div>
                    <div class="bar-segment bar-segment-moderate" style="width: ${moderatePct}%"></div>
                    <div class="bar-segment bar-segment-severe" style="width: ${severePct}%"></div>
                </div>
                <div class="bar-chart-count">${displayValue}</div>
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
    } else if (currentGroupBy === 'capacity') {
        data = violationsData.by_capacity || [];
        labelKey = 'capacity_bin';
    }
    
    if (!data || data.length === 0) {
        container.innerHTML = '<div style="color: #666; font-size: 0.9em; font-style: italic; padding: 20px; text-align: center;">No data available</div>';
        return;
    }
    
    // For capacity grouping, don't allow capacity normalization (doesn't make sense)
    const useNormalized = capacityNormalized && currentGroupBy !== 'capacity';
    
    // Keep capacity bins in original order (already sorted by bins), sort others by total
    const sortByTotal = currentGroupBy !== 'capacity';
    
    renderStackedBarChart('byGroupedChart', data, labelKey, sortByTotal, useNormalized);
}

function setupGroupByDropdown() {
    const dropdown = document.getElementById('groupBySelect');
    if (!dropdown) return;
    
    dropdown.addEventListener('change', (e) => {
        currentGroupBy = e.target.value;
        renderGroupedChart();
    });
}

function setupCapacityNormalizedCheckbox() {
    const checkbox = document.getElementById('capacityNormalizedCheckbox');
    if (!checkbox) return;
    
    checkbox.addEventListener('change', (e) => {
        capacityNormalized = e.target.checked;
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
