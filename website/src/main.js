// Main application logic
let allAgencies = [];
let filteredAgencies = [];

// Load and display data
async function init() {
    try {
        // Fetch the agency data
        const response = await fetch('/data/agencies_data.json');
        if (!response.ok) {
            throw new Error(`Failed to load data: ${response.statusText}`);
        }
        
        allAgencies = await response.json();
        filteredAgencies = allAgencies;
        
        hideLoading();
        displayStats();
        displayAgencies(allAgencies);
        setupSearch();
        
    } catch (error) {
        console.error('Error loading data:', error);
        showError(`Failed to load data: ${error.message}`);
        hideLoading();
    }
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function showError(message) {
    const errorEl = document.getElementById('error');
    errorEl.textContent = message;
    errorEl.style.display = 'block';
}

function displayStats() {
    const statsEl = document.getElementById('stats');
    
    const totalAgencies = allAgencies.length;
    const totalViolations = allAgencies.reduce((sum, a) => sum + a.total_violations, 0);
    const totalReports = allAgencies.reduce((sum, a) => sum + a.total_reports, 0);
    const agenciesWithViolations = allAgencies.filter(a => a.total_violations > 0).length;
    
    statsEl.innerHTML = `
        <div class="stat-card">
            <div class="stat-number">${totalAgencies}</div>
            <div class="stat-label">Total Agencies</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${totalViolations}</div>
            <div class="stat-label">Total Violations</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${agenciesWithViolations}</div>
            <div class="stat-label">Agencies with Violations</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${totalReports}</div>
            <div class="stat-label">Reports/Inspections</div>
        </div>
    `;
}

function displayAgencies(agencies) {
    const agenciesEl = document.getElementById('agencies');
    const noResultsEl = document.getElementById('noResults');
    
    if (agencies.length === 0) {
        agenciesEl.innerHTML = '';
        noResultsEl.style.display = 'block';
        return;
    }
    
    noResultsEl.style.display = 'none';
    
    agenciesEl.innerHTML = agencies.map(agency => {
        return `
            <div class="agency-card" data-agency-id="${agency.agencyId}">
                <div class="agency-header">
                    <div>
                        <div class="agency-name">${escapeHtml(agency.AgencyName || 'Unknown Agency')}</div>
                        <div style="color: #666; font-size: 0.9em; margin-top: 4px;">ID: ${escapeHtml(agency.agencyId)}</div>
                    </div>
                </div>
                
                <div class="agency-stats">
                    <span class="stat-badge violations-badge">
                        ⚠️ ${agency.total_violations} Violations
                    </span>
                    <span class="stat-badge reports-badge">
                        📋 ${agency.total_reports} Reports
                    </span>
                </div>
                
                <div class="agency-details" id="details-${agency.agencyId}">
                    ${renderViolations(agency.violations)}
                </div>
            </div>
        `;
    }).join('');
    
    // Add click handlers to expand/collapse details
    document.querySelectorAll('.agency-card').forEach(card => {
        card.addEventListener('click', (e) => {
            const agencyId = card.dataset.agencyId;
            const details = document.getElementById(`details-${agencyId}`);
            details.classList.toggle('visible');
        });
    });
}

function renderViolations(violations) {
    if (!violations || violations.length === 0) {
        return `
            <div class="violations-list">
                <div class="section-title">Violations & Reports</div>
                <p style="color: #666;">No reports available.</p>
            </div>
        `;
    }
    
    // Sort by date (most recent first)
    const sortedViolations = [...violations].sort((a, b) => {
        return new Date(b.date_processed) - new Date(a.date_processed);
    });
    
    const violationItems = sortedViolations.map(v => {
        const hasViolations = v.num_violations > 0;
        const violationClass = hasViolations ? 'has-violations' : '';
        
        return `
            <div class="violation-item ${violationClass}">
                <div class="date">${escapeHtml(v.date || 'Date not specified')}</div>
                ${v.agency_name ? `<div style="font-weight: 500;">${escapeHtml(v.agency_name)}</div>` : ''}
                ${hasViolations ? `
                    <div class="violations-text">
                        ${v.num_violations} violation${v.num_violations > 1 ? 's' : ''}: 
                        ${escapeHtml(v.violations_list)}
                    </div>
                ` : `
                    <div style="color: #27ae60;">✓ No violations found</div>
                `}
            </div>
        `;
    }).join('');
    
    return `
        <div class="violations-list">
            <div class="section-title">Violations & Reports (${violations.length})</div>
            ${violationItems}
        </div>
    `;
}

function setupSearch() {
    const searchInput = document.getElementById('searchInput');
    
    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase().trim();
        
        if (!searchTerm) {
            filteredAgencies = allAgencies;
        } else {
            filteredAgencies = allAgencies.filter(agency => {
                return (
                    agency.AgencyName?.toLowerCase().includes(searchTerm) ||
                    agency.agencyId?.toLowerCase().includes(searchTerm)
                );
            });
        }
        
        displayAgencies(filteredAgencies);
    });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize the application
init();
