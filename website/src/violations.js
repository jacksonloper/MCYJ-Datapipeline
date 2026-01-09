// Violations analytics page - displays violation statistics
// with views by date, facility type, and age group

let violationsData = null;
let currentMonthView = 'all'; // 'all', 'recent12', 'recent24'

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
        renderByMonthChart();
        renderByFacilityTypeChart();
        renderByAgeGroupChart();
        setupViewToggle();
        
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

function renderByMonthChart() {
    if (!violationsData || !violationsData.by_month) return;
    
    let data = [...violationsData.by_month];
    
    // Sort months chronologically before filtering to ensure recent months are correct
    data.sort((a, b) => a.month.localeCompare(b.month));
    
    // Filter based on current view (after sorting)
    if (currentMonthView === 'recent12') {
        data = data.slice(-12);
    } else if (currentMonthView === 'recent24') {
        data = data.slice(-24);
    }
    
    renderStackedBarChart('byMonthChart', data, 'month', false);
}

function renderByFacilityTypeChart() {
    if (!violationsData || !violationsData.by_facility_type) return;
    
    renderStackedBarChart('byFacilityTypeChart', violationsData.by_facility_type, 'facility_type', true);
}

function renderByAgeGroupChart() {
    if (!violationsData || !violationsData.by_facility_age) return;
    
    const data = violationsData.by_facility_age;
    
    if (!data || data.length === 0) {
        const containers = ['byAgeGroupChartLow', 'byAgeGroupChartModerate', 'byAgeGroupChartSevere'];
        containers.forEach(id => {
            const container = document.getElementById(id);
            if (container) {
                container.innerHTML = '<div style="color: #666; font-size: 0.9em; font-style: italic; padding: 20px; text-align: center;">No age data available</div>';
            }
        });
        return;
    }
    
    // Render three separate charts for each severity level
    renderSeverityAgeChart('byAgeGroupChartLow', data, 'low', '#f1c40f', 'Low Severity');
    renderSeverityAgeChart('byAgeGroupChartModerate', data, 'moderate', '#e67e22', 'Moderate Severity');
    renderSeverityAgeChart('byAgeGroupChartSevere', data, 'severe', '#e74c3c', 'Severe Severity');
}

function renderSeverityAgeChart(containerId, data, severityKey, fillColor, title) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // Filter to only facilities that have violations of this severity
    const filteredData = data.filter(d => d[severityKey] > 0);
    
    if (filteredData.length === 0) {
        container.innerHTML = '<div style="color: #666; font-size: 0.9em; font-style: italic; padding: 20px; text-align: center;">No violations of this severity</div>';
        return;
    }
    
    // Chart dimensions - responsive
    const chartWidth = 400;
    const chartHeight = 300;
    const margin = { top: 20, right: 20, bottom: 40, left: 50 };
    const innerWidth = chartWidth - margin.left - margin.right;
    const innerHeight = chartHeight - margin.top - margin.bottom;
    
    // Find age range for scaling (y-axis) - use full data range for consistency across charts
    const minAge = Math.min(...data.map(d => d.min_age));
    const maxAge = Math.max(...data.map(d => d.max_age));
    const ageRange = (maxAge - minAge) > 0 ? (maxAge - minAge) : 1;
    
    // Y scale: age (younger ages at bottom, older at top)
    const yScale = (age) => innerHeight - ((age - minAge) / ageRange) * innerHeight;
    
    // Sort by starting age, then by ending age
    const sortedData = [...filteredData].sort((a, b) => a.min_age - b.min_age || a.max_age - b.max_age);
    
    // Calculate bar widths such that area is proportional to violations of this severity
    const barsWithMetrics = sortedData.map(item => {
        const heightInYears = (item.max_age - item.min_age) > 0 ? (item.max_age - item.min_age) : 1;
        const violations = item[severityKey];
        // Area should be proportional to violations, so width = violations / heightInYears
        const widthRatio = violations / heightInYears;
        return { ...item, widthRatio, violations };
    });
    
    const maxWidthRatio = Math.max(...barsWithMetrics.map(d => d.widthRatio));
    const widthScale = (widthRatio) => maxWidthRatio > 0 ? (widthRatio / maxWidthRatio) * innerWidth * 0.9 : 2;
    
    // Build SVG with proper viewBox for responsiveness
    let svg = `<svg viewBox="0 0 ${chartWidth} ${chartHeight}" preserveAspectRatio="xMidYMid meet" style="width: 100%; height: auto; display: block; max-width: 100%;">`;
    
    // Background
    svg += `<rect x="0" y="0" width="${chartWidth}" height="${chartHeight}" fill="#fafafa"/>`;
    
    // Chart area group
    svg += `<g transform="translate(${margin.left}, ${margin.top})">`;
    
    // Y-axis gridlines and labels (age)
    for (let age = minAge; age <= maxAge; age += 2) {
        const y = yScale(age);
        // Gridline
        svg += `<line x1="0" y1="${y}" x2="${innerWidth}" y2="${y}" stroke="#e0e0e0" stroke-width="1"/>`;
        // Label
        svg += `<text x="-8" y="${y}" dy="0.35em" text-anchor="end" font-size="10" fill="#666">${age}</text>`;
    }
    
    // Y-axis line
    svg += `<line x1="0" y1="0" x2="0" y2="${innerHeight}" stroke="#333" stroke-width="1"/>`;
    
    // Y-axis label
    svg += `<text x="${-margin.left + 12}" y="${innerHeight / 2}" transform="rotate(-90, ${-margin.left + 12}, ${innerHeight / 2})" text-anchor="middle" font-size="10" fill="#333">Age</text>`;
    
    // X-axis line
    svg += `<line x1="0" y1="${innerHeight}" x2="${innerWidth}" y2="${innerHeight}" stroke="#333" stroke-width="1"/>`;
    
    // X-axis label
    svg += `<text x="${innerWidth / 2}" y="${innerHeight + 30}" text-anchor="middle" font-size="10" fill="#666">Violations (area ∝ count)</text>`;
    
    // Draw bars - stack horizontally (x position increases as we go)
    let xOffset = 0;
    
    for (const item of barsWithMetrics) {
        const y1 = yScale(item.max_age); // top of bar (older age)
        const y2 = yScale(item.min_age); // bottom of bar (younger age)
        const barHeight = Math.max(Math.abs(y2 - y1), 3); // minimum 3px height
        const barWidth = Math.max(widthScale(item.widthRatio), 2); // minimum 2px width
        
        // Tooltip content
        const tooltip = `${item.facility_name}\nAges: ${item.min_age}-${item.max_age}\n${title}: ${item.violations}`;
        
        // Draw bar
        svg += `<rect x="${xOffset}" y="${Math.min(y1, y2)}" width="${barWidth}" height="${barHeight}" fill="${fillColor}" stroke="#fff" stroke-width="0.5" opacity="0.85"><title>${tooltip}</title></rect>`;
        
        // Move x offset for next bar
        xOffset += barWidth;
    }
    
    svg += `</g></svg>`;
    
    // Add summary info
    const totalViolations = filteredData.reduce((sum, d) => sum + d[severityKey], 0);
    const summaryHtml = `
        <div style="margin-bottom: 8px; font-size: 0.85em; color: #666;">
            <strong>${filteredData.length}</strong> facilities, 
            <strong>${totalViolations}</strong> violations
        </div>
    `;
    
    container.innerHTML = summaryHtml + svg;
}

function setupViewToggle() {
    const showAllBtn = document.getElementById('showAllMonths');
    const showRecent12Btn = document.getElementById('showRecent12');
    const showRecent24Btn = document.getElementById('showRecent24');
    
    if (!showAllBtn || !showRecent12Btn || !showRecent24Btn) return;
    
    function updateButtons() {
        showAllBtn.classList.toggle('active', currentMonthView === 'all');
        showRecent12Btn.classList.toggle('active', currentMonthView === 'recent12');
        showRecent24Btn.classList.toggle('active', currentMonthView === 'recent24');
    }
    
    showAllBtn.addEventListener('click', () => {
        currentMonthView = 'all';
        updateButtons();
        renderByMonthChart();
    });
    
    showRecent12Btn.addEventListener('click', () => {
        currentMonthView = 'recent12';
        updateButtons();
        renderByMonthChart();
    });
    
    showRecent24Btn.addEventListener('click', () => {
        currentMonthView = 'recent24';
        updateButtons();
        renderByMonthChart();
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
