// Violations analytics page - displays violation statistics
// with views by date and facility type/region/gender/capacity.
// 
// IMPORTANT: Only facilities with currently active licenses are included.
// Normalization divides by (capacity × years_active) to account for both
// facility size and how long it has been operating.

import noUiSlider from 'nouislider';
import 'nouislider/dist/nouislider.css';

let violationsData = null;
let currentGroupBy = 'facility_type'; // 'facility_type', 'region', 'gender', 'capacity', 'years_active'
let facilityCountGroupBy = 'facility_type';
let capacityNormalized = false;
let yearRangeMin = null;
let yearRangeMax = null;
let yearSlider = null;

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
        renderMethodologyNote();
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

function renderMethodologyNote() {
    const container = document.getElementById('methodologyNote');
    if (!container || !violationsData || !violationsData.metadata) return;
    
    const meta = violationsData.metadata;
    const methodology = meta.methodology || {};
    
    container.innerHTML = `
        <details>
            <summary>📋 Data Methodology & Filtering</summary>
            <div class="methodology-content">
                <p><strong>Filtering:</strong> ${escapeHtml(methodology.filtering || 'Only facilities with currently active licenses are included.')}</p>
                <p><strong>Years Active Estimation:</strong> ${escapeHtml(methodology.years_active_estimation || 'Years active is estimated from the earliest document we have for each facility.')}</p>
                <p><strong>Capacity Normalization:</strong> ${escapeHtml(methodology.capacity_normalization || 'When normalizing, values are divided by (capacity × years_active).')}</p>
                ${methodology.caveats && methodology.caveats.length > 0 ? `
                <p><strong>Caveats:</strong></p>
                <ul>
                    ${methodology.caveats.map(c => `<li>${escapeHtml(c)}</li>`).join('')}
                </ul>
                ` : ''}
                <p class="metadata-stats">
                    <em>Active facilities: ${meta.active_facility_count || 'N/A'} • 
                    Violations from inactive facilities excluded: ${meta.skipped_inactive_facilities || 0}</em>
                </p>
            </div>
        </details>
    `;
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
    
    // Filter out items with no capacity_years if normalized mode is on
    // Also filter out "Unknown" category since those facilities don't have capacity data
    let filteredData = [...data];
    if (normalized) {
        filteredData = filteredData.filter(d => {
            const label = d[labelKey] || '';
            // Exclude Unknown categories and items with no capacity_years
            if (label === 'Unknown') return false;
            // Use capacity_years if available, fall back to capacity
            const normValue = d.capacity_years || d.capacity || 0;
            return normValue > 0;
        });
        if (filteredData.length === 0) {
            container.innerHTML = '<div style="color: #666; font-size: 0.9em; font-style: italic; padding: 20px; text-align: center;">No data available with known capacity and years active</div>';
            return;
        }
    }
    
    // Sort data by total (descending) if requested, otherwise keep original order
    let sortedData = [...filteredData];
    if (sortByTotal) {
        if (normalized) {
            // Sort by normalized value (total / capacity_years)
            sortedData.sort((a, b) => {
                const aNorm = a.capacity_years || a.capacity || 0;
                const bNorm = b.capacity_years || b.capacity || 0;
                const aVal = aNorm > 0 ? a.total / aNorm : 0;
                const bVal = bNorm > 0 ? b.total / bNorm : 0;
                return bVal - aVal;
            });
        } else {
            sortedData.sort((a, b) => (b.total || 0) - (a.total || 0));
        }
    }
    
    // Calculate max value for scaling
    let maxValue;
    if (normalized) {
        maxValue = Math.max(...sortedData.map(d => {
            const normValue = d.capacity_years || d.capacity || 0;
            return normValue > 0 ? d.total / normValue : 0;
        }));
    } else {
        maxValue = Math.max(...sortedData.map(d => d.total || 0));
    }
    
    const barsHtml = sortedData.map(item => {
        const total = item.total || 0;
        const low = item.low || 0;
        const moderate = item.moderate || 0;
        const severe = item.severe || 0;
        const capacity = item.capacity || 0;
        const capacityYears = item.capacity_years || 0;
        // Use capacity_years if available, otherwise fall back to capacity
        const normValue = capacityYears > 0 ? capacityYears : capacity;
        
        let displayValue, lowPct, moderatePct, severePct;
        
        if (normalized && normValue > 0) {
            // Normalized mode: divide by capacity_years (or capacity as fallback)
            const normalizedTotal = total / normValue;
            // Use 2 decimal places for better readability
            displayValue = normalizedTotal.toFixed(2);
            lowPct = maxValue > 0 ? ((low / normValue) / maxValue) * 100 : 0;
            moderatePct = maxValue > 0 ? ((moderate / normValue) / maxValue) * 100 : 0;
            severePct = maxValue > 0 ? ((severe / normValue) / maxValue) * 100 : 0;
        } else {
            displayValue = total.toString();
            lowPct = maxValue > 0 ? (low / maxValue) * 100 : 0;
            moderatePct = maxValue > 0 ? (moderate / maxValue) * 100 : 0;
            severePct = maxValue > 0 ? (severe / maxValue) * 100 : 0;
        }
        
        const label = item[labelKey] || 'Unknown';
        let tooltip;
        if (normalized && normValue > 0) {
            if (capacityYears > 0) {
                tooltip = `Low: ${low}, Moderate: ${moderate}, Severe: ${severe} (Capacity×Years: ${capacityYears.toFixed(1)})`;
            } else {
                tooltip = `Low: ${low}, Moderate: ${moderate}, Severe: ${severe} (Capacity: ${capacity})`;
            }
        } else {
            tooltip = `Low: ${low}, Moderate: ${moderate}, Severe: ${severe}`;
        }
        
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
    const sliderContainer = document.getElementById('yearRangeSlider');
    const minLabel = document.getElementById('yearRangeMinLabel');
    const maxLabel = document.getElementById('yearRangeMaxLabel');
    
    if (!sliderContainer || !violationsData.by_year || violationsData.by_year.length === 0) return;
    
    const years = violationsData.by_year.map(y => parseInt(y.year)).sort((a, b) => a - b);
    const minYear = years[0];
    const maxYear = years[years.length - 1];
    
    // Initialize year range
    if (!yearRangeMin) yearRangeMin = minYear;
    if (!yearRangeMax) yearRangeMax = maxYear;
    
    // Create noUiSlider with dual handles
    yearSlider = noUiSlider.create(sliderContainer, {
        start: [yearRangeMin, yearRangeMax],
        connect: true,
        step: 1,
        range: {
            'min': minYear,
            'max': maxYear
        },
        format: {
            to: value => Math.round(value),
            from: value => Math.round(value)
        },
        tooltips: false,
        pips: {
            mode: 'steps',
            density: 100
        }
    });
    
    // Update labels initially
    if (minLabel) minLabel.textContent = yearRangeMin;
    if (maxLabel) maxLabel.textContent = yearRangeMax;
    
    // Listen for slider changes
    yearSlider.on('update', (values) => {
        const newMin = parseInt(values[0]);
        const newMax = parseInt(values[1]);
        
        if (minLabel) minLabel.textContent = newMin;
        if (maxLabel) maxLabel.textContent = newMax;
    });
    
    yearSlider.on('change', (values) => {
        yearRangeMin = parseInt(values[0]);
        yearRangeMax = parseInt(values[1]);
        
        renderGroupedChart();
        renderFacilityCountChart();
    });
}

function getFilteredDataByYearRange(groupingType) {
    if (!violationsData.per_year) return null;
    
    // Map grouping type to the correct key in the data
    let labelKey;
    if (groupingType === 'capacity') {
        labelKey = 'capacity_bin';
    } else if (groupingType === 'years_active') {
        labelKey = 'years_active_bin';
    } else {
        labelKey = groupingType;
    }
    
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
                aggregated[key] = { total: 0, low: 0, moderate: 0, severe: 0, capacity: 0, capacity_years: 0 };
            }
            aggregated[key].total += item.total || 0;
            aggregated[key].low += item.low || 0;
            aggregated[key].moderate += item.moderate || 0;
            aggregated[key].severe += item.severe || 0;
            aggregated[key].capacity += item.capacity || 0;
            aggregated[key].capacity_years += item.capacity_years || 0;
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
    
    // Sort years active bins in order
    if (groupingType === 'years_active') {
        const order = {'<1 year': 0, '1-2 years': 1, '2-3 years': 2, '3-5 years': 3, '5-10 years': 4, '10+ years': 5, 'Unknown': 6};
        result.sort((a, b) => (order[a.years_active_bin] || 99) - (order[b.years_active_bin] || 99));
    }
    
    return result;
}

function renderGroupedChart() {
    const container = document.getElementById('byGroupedChart');
    if (!container) return;
    
    let data = [];
    let labelKey = '';
    
    // Map grouping type to label key
    if (currentGroupBy === 'capacity') {
        labelKey = 'capacity_bin';
    } else if (currentGroupBy === 'years_active') {
        labelKey = 'years_active_bin';
    } else {
        labelKey = currentGroupBy;
    }
    
    // Try to use year-filtered data if available
    if (violationsData.per_year && yearRangeMin && yearRangeMax) {
        data = getFilteredDataByYearRange(currentGroupBy);
    } else {
        // Fall back to pre-aggregated data
        if (currentGroupBy === 'facility_type') {
            data = violationsData.by_facility_type || [];
        } else if (currentGroupBy === 'region') {
            data = violationsData.by_region || [];
        } else if (currentGroupBy === 'gender') {
            data = violationsData.by_gender || [];
        } else if (currentGroupBy === 'capacity') {
            data = violationsData.by_capacity || [];
        } else if (currentGroupBy === 'years_active') {
            data = violationsData.by_years_active || [];
        }
    }
    
    if (!data || data.length === 0) {
        container.innerHTML = '<div style="color: #666; font-size: 0.9em; font-style: italic; padding: 20px; text-align: center;">No data available</div>';
        return;
    }
    
    // Allow capacity normalization for all groupings except years_active
    const useNormalized = capacityNormalized && currentGroupBy !== 'years_active';
    
    // Keep capacity bins and years_active bins in original order (already sorted), sort others by total
    const sortByTotal = currentGroupBy !== 'capacity' && currentGroupBy !== 'years_active';
    
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
    
    // Map grouping type to label key
    let labelKey;
    if (groupingType === 'capacity') {
        labelKey = 'capacity_bin';
    } else if (groupingType === 'years_active') {
        labelKey = 'years_active_bin';
    } else {
        labelKey = groupingType;
    }
    
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
    
    // Sort years active bins in order
    if (groupingType === 'years_active') {
        const order = {'<1 year': 0, '1-2 years': 1, '2-3 years': 2, '3-5 years': 3, '5-10 years': 4, '10+ years': 5, 'Unknown': 6};
        result.sort((a, b) => (order[a.years_active_bin] || 99) - (order[b.years_active_bin] || 99));
    }
    
    return result;
}

function renderFacilityCountChart() {
    const container = document.getElementById('facilityCountChart');
    if (!container) return;
    
    let data = getFilteredFacilityCountsByYearRange(facilityCountGroupBy);
    
    // Map grouping type to label key
    let labelKey;
    if (facilityCountGroupBy === 'capacity') {
        labelKey = 'capacity_bin';
    } else if (facilityCountGroupBy === 'years_active') {
        labelKey = 'years_active_bin';
    } else {
        labelKey = facilityCountGroupBy;
    }
    
    if (!data || data.length === 0) {
        container.innerHTML = '<div style="color: #666; font-size: 0.9em; font-style: italic; padding: 20px; text-align: center;">No data available</div>';
        return;
    }
    
    // Sort by count descending (except capacity bins and years_active bins)
    let sortedData = [...data];
    if (facilityCountGroupBy !== 'capacity' && facilityCountGroupBy !== 'years_active') {
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
