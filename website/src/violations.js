// Violations analytics page - displays violation statistics
// with views by date and facility type/region/gender/capacity.

let violationsData = null;
let currentGroupBy = 'facility_type'; // 'facility_type', 'region', 'gender', 'capacity'
let facilityCountGroupBy = 'facility_type';
let capacityNormalized = false;
let yearRangeMin = null;
let yearRangeMax = null;

// Load and display data
async function init() {
    try {
        const response = await fetch('/data/violations_data.json');
        if (!response.ok) {
            throw new Error(`Failed to load data: ${response.statusText}`);
        }
        
        violationsData = await response.json();
        
        // Initialize year range from data
        if (violationsData.metadata && violationsData.metadata.year_range) {
            yearRangeMin = parseInt(violationsData.metadata.year_range.min);
            yearRangeMax = parseInt(violationsData.metadata.year_range.max);
        } else if (violationsData.by_year && violationsData.by_year.length > 0) {
            yearRangeMin = parseInt(violationsData.by_year[0].year);
            yearRangeMax = parseInt(violationsData.by_year[violationsData.by_year.length - 1].year);
        }
        
        hideLoading();
        showContent();
        renderSummaryStats();
        renderByYearChart();
        setupYearRangeSlider();
        renderGroupedChart();
        setupGroupByDropdown();
        setupCapacityNormalizedCheckbox();
        renderFacilityCountChart();
        setupFacilityCountDropdown();
        
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
    // Also filter out "Unknown" category since those facilities don't have capacity data
    let filteredData = [...data];
    if (normalized) {
        filteredData = filteredData.filter(d => {
            const label = d[labelKey] || '';
            // Exclude Unknown categories and items with no capacity
            if (label === 'Unknown') return false;
            return d.capacity && d.capacity > 0;
        });
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

function setupYearRangeSlider() {
    const minSlider = document.getElementById('yearRangeMin');
    const maxSlider = document.getElementById('yearRangeMax');
    const minLabel = document.getElementById('yearRangeMinLabel');
    const maxLabel = document.getElementById('yearRangeMaxLabel');
    
    if (!minSlider || !maxSlider || !violationsData.by_year || violationsData.by_year.length === 0) return;
    
    const years = violationsData.by_year.map(y => parseInt(y.year)).sort((a, b) => a - b);
    const minYear = years[0];
    const maxYear = years[years.length - 1];
    
    // Set slider attributes
    minSlider.min = minYear;
    minSlider.max = maxYear;
    minSlider.value = yearRangeMin || minYear;
    
    maxSlider.min = minYear;
    maxSlider.max = maxYear;
    maxSlider.value = yearRangeMax || maxYear;
    
    // Update labels
    if (minLabel) minLabel.textContent = minSlider.value;
    if (maxLabel) maxLabel.textContent = maxSlider.value;
    
    // Add event listeners
    minSlider.addEventListener('input', (e) => {
        const val = parseInt(e.target.value);
        if (val > parseInt(maxSlider.value)) {
            minSlider.value = maxSlider.value;
        }
        yearRangeMin = parseInt(minSlider.value);
        if (minLabel) minLabel.textContent = yearRangeMin;
        renderGroupedChart();
        renderFacilityCountChart();
    });
    
    maxSlider.addEventListener('input', (e) => {
        const val = parseInt(e.target.value);
        if (val < parseInt(minSlider.value)) {
            maxSlider.value = minSlider.value;
        }
        yearRangeMax = parseInt(maxSlider.value);
        if (maxLabel) maxLabel.textContent = yearRangeMax;
        renderGroupedChart();
        renderFacilityCountChart();
    });
}

function getFilteredDataByYearRange(groupingType) {
    if (!violationsData.per_year) return null;
    
    const labelKey = groupingType === 'capacity' ? 'capacity_bin' : groupingType;
    
    // Aggregate data across selected years
    const aggregated = {};
    
    for (let year = yearRangeMin; year <= yearRangeMax; year++) {
        const yearStr = String(year);
        const yearData = violationsData.per_year[yearStr];
        if (!yearData) continue;
        
        const groupData = yearData[labelKey] || [];
        for (const item of groupData) {
            const key = item[labelKey];
            if (!aggregated[key]) {
                aggregated[key] = { total: 0, low: 0, moderate: 0, severe: 0, capacity: 0 };
            }
            aggregated[key].total += item.total || 0;
            aggregated[key].low += item.low || 0;
            aggregated[key].moderate += item.moderate || 0;
            aggregated[key].severe += item.severe || 0;
            aggregated[key].capacity += item.capacity || 0;
        }
    }
    
    // Convert to array
    const result = Object.entries(aggregated).map(([key, counts]) => ({
        [labelKey]: key,
        ...counts
    }));
    
    // Sort capacity bins in order
    if (groupingType === 'capacity') {
        const order = {'1-10': 0, '11-20': 1, '21-30': 2, '31-50': 3, '51-100': 4, '100+': 5, 'Unknown': 6};
        result.sort((a, b) => (order[a.capacity_bin] || 99) - (order[b.capacity_bin] || 99));
    }
    
    return result;
}

function renderGroupedChart() {
    const container = document.getElementById('byGroupedChart');
    if (!container) return;
    
    let data = [];
    let labelKey = '';
    
    // Try to use year-filtered data if available
    if (violationsData.per_year && yearRangeMin && yearRangeMax) {
        data = getFilteredDataByYearRange(currentGroupBy);
        labelKey = currentGroupBy === 'capacity' ? 'capacity_bin' : currentGroupBy;
    } else {
        // Fall back to pre-aggregated data
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
    }
    
    if (!data || data.length === 0) {
        container.innerHTML = '<div style="color: #666; font-size: 0.9em; font-style: italic; padding: 20px; text-align: center;">No data available</div>';
        return;
    }
    
    // Allow capacity normalization for all groupings including capacity
    const useNormalized = capacityNormalized;
    
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

// Facility Count Section
function getFilteredFacilityCountsByYearRange(groupingType) {
    if (!violationsData.facility_counts_per_year) return null;
    
    const labelKey = groupingType === 'capacity' ? 'capacity_bin' : groupingType;
    
    // Aggregate unique facilities across selected years
    const aggregated = {};
    
    for (let year = yearRangeMin; year <= yearRangeMax; year++) {
        const yearStr = String(year);
        const yearData = violationsData.facility_counts_per_year[yearStr];
        if (!yearData) continue;
        
        const groupData = yearData[labelKey] || [];
        for (const item of groupData) {
            const key = item[labelKey];
            if (!aggregated[key]) {
                aggregated[key] = 0;
            }
            // Note: This will double-count facilities across years
            // For accurate unique counts, we'd need to track facility IDs
            // For now, use the max count across years as an approximation
            aggregated[key] = Math.max(aggregated[key], item.count || 0);
        }
    }
    
    // Convert to array
    const result = Object.entries(aggregated).map(([key, count]) => ({
        [labelKey]: key,
        count
    }));
    
    // Sort capacity bins in order
    if (groupingType === 'capacity') {
        const order = {'1-10': 0, '11-20': 1, '21-30': 2, '31-50': 3, '51-100': 4, '100+': 5, 'Unknown': 6};
        result.sort((a, b) => (order[a.capacity_bin] || 99) - (order[b.capacity_bin] || 99));
    }
    
    return result;
}

function renderFacilityCountChart() {
    const container = document.getElementById('facilityCountChart');
    if (!container) return;
    
    let data = getFilteredFacilityCountsByYearRange(facilityCountGroupBy);
    const labelKey = facilityCountGroupBy === 'capacity' ? 'capacity_bin' : facilityCountGroupBy;
    
    if (!data || data.length === 0) {
        container.innerHTML = '<div style="color: #666; font-size: 0.9em; font-style: italic; padding: 20px; text-align: center;">No data available</div>';
        return;
    }
    
    // Sort by count descending (except capacity bins)
    let sortedData = [...data];
    if (facilityCountGroupBy !== 'capacity') {
        sortedData.sort((a, b) => (b.count || 0) - (a.count || 0));
    }
    
    // Find max for scaling
    const maxCount = Math.max(...sortedData.map(d => d.count || 0));
    
    const barsHtml = sortedData.map(item => {
        const count = item.count || 0;
        const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
        const label = item[labelKey] || 'Unknown';
        
        return `
            <div class="bar-chart-row">
                <div class="bar-chart-label" title="${escapeHtml(label)}">${escapeHtml(label)}</div>
                <div class="bar-chart-bar-container" title="${count} facilities">
                    <div class="bar-segment" style="width: ${pct}%; background: #3498db;"></div>
                </div>
                <div class="bar-chart-count">${count}</div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = barsHtml;
}

function setupFacilityCountDropdown() {
    const dropdown = document.getElementById('facilityCountGroupBySelect');
    if (!dropdown) return;
    
    dropdown.addEventListener('change', (e) => {
        facilityCountGroupBy = e.target.value;
        renderFacilityCountChart();
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
