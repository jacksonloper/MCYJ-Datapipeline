// Main application logic
import { parquetRead } from 'hyparquet';

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
        setupModal();
        
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
            // Don't toggle details if clicking on the view report button
            if (e.target.classList.contains('view-report-btn')) {
                e.stopPropagation();
                const sha256 = e.target.dataset.sha256;
                viewReport(sha256);
                return;
            }
            
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
                <button class="view-report-btn" data-sha256="${escapeHtml(v.sha256)}">
                    📄 View Full Report
                </button>
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

// Setup modal functionality
function setupModal() {
    const modal = document.getElementById('reportModal');
    const closeBtn = document.getElementById('closeModal');
    
    // Close modal when clicking close button
    closeBtn.addEventListener('click', () => {
        modal.classList.remove('visible');
    });
    
    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('visible');
        }
    });
    
    // Close modal on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('visible')) {
            modal.classList.remove('visible');
        }
    });
}

// View report text from parquet files using hyparquet
async function viewReport(sha256) {
    const modal = document.getElementById('reportModal');
    const modalLoading = document.getElementById('modalLoading');
    const modalError = document.getElementById('modalError');
    const modalText = document.getElementById('modalText');
    
    // Show modal and loading state
    modal.classList.add('visible');
    modalLoading.style.display = 'block';
    modalError.style.display = 'none';
    modalText.style.display = 'none';
    
    try {
        // Get list of parquet files
        const parquetFiles = [
            '/parquet/20251103_133347_pdf_text.parquet',
            '/parquet/20251103_133526_pdf_text.parquet',
            '/parquet/20251103_133758_pdf_text.parquet',
            '/parquet/20251103_134410_pdf_text.parquet',
            '/parquet/20251103_142412_pdf_text.parquet'
        ];
        
        let reportText = null;
        
        // Search through parquet files using hyparquet
        for (const file of parquetFiles) {
            try {
                console.log(`Searching in ${file}...`);
                
                // Fetch the parquet file
                const response = await fetch(file);
                if (!response.ok) continue;
                
                const arrayBuffer = await response.arrayBuffer();
                
                // Parse the parquet file and search for the sha256
                await parquetRead({
                    file: arrayBuffer,
                    onComplete: (data) => {
                        // data is an array of row objects
                        for (const row of data) {
                            if (row.sha256 === sha256) {
                                reportText = row.text;
                                break;
                            }
                        }
                    }
                });
                
                if (reportText) {
                    console.log(`Found report in ${file}`);
                    break;
                }
            } catch (err) {
                console.warn(`Error reading ${file}:`, err);
                continue;
            }
        }
        
        if (!reportText) {
            throw new Error('Report not found in parquet files');
        }
        
        // Parse the text if it's stored as a string representation of an array
        let fullText = '';
        try {
            // The text might be stored as a string representation of a list
            const textPages = typeof reportText === 'string' && reportText.startsWith('[') 
                ? JSON.parse(reportText.replace(/'/g, '"')) 
                : reportText;
            
            if (Array.isArray(textPages)) {
                fullText = textPages.join('\n\n--- Page Break ---\n\n');
            } else {
                fullText = String(reportText);
            }
        } catch (parseError) {
            console.warn('Error parsing text:', parseError);
            fullText = String(reportText);
        }
        
        // Display the text
        modalLoading.style.display = 'none';
        modalText.style.display = 'block';
        modalText.textContent = fullText;
        
    } catch (error) {
        console.error('Error loading report:', error);
        modalLoading.style.display = 'none';
        modalError.style.display = 'block';
        modalError.textContent = `Failed to load report: ${error.message}`;
    }
}

// Initialize the application
init();
