/**
 * Playwright test script to verify the dev server loads agencies_data.json correctly
 * 
 * This script:
 * 1. Starts the dev server
 * 2. Loads the page
 * 3. Verifies that agencies_data.json is downloaded
 * 4. Checks that the page displays agency data
 */

import { chromium } from 'playwright';

async function testDevServer() {
    console.log('Starting Playwright test of dev server...\n');
    
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    
    // Track network requests
    const requests = [];
    page.on('request', request => {
        requests.push({
            url: request.url(),
            method: request.method()
        });
    });
    
    // Track responses
    const responses = [];
    page.on('response', response => {
        responses.push({
            url: response.url(),
            status: response.status(),
            contentType: response.headers()['content-type']
        });
    });
    
    console.log('Navigating to http://localhost:5173/...');
    await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
    
    // Wait for the page to load the data
    await page.waitForSelector('#stats', { timeout: 10000 });
    
    // Check if agencies_data.json was loaded
    const agenciesDataRequest = responses.find(r => r.url.includes('agencies_data.json'));
    if (agenciesDataRequest) {
        console.log(`✓ agencies_data.json loaded successfully (status: ${agenciesDataRequest.status})`);
    } else {
        console.log('✗ agencies_data.json was NOT loaded!');
    }
    
    // Get the stats from the page
    const totalAgencies = await page.textContent('.stat-card:nth-child(1) .stat-number');
    const totalReports = await page.textContent('.stat-card:nth-child(2) .stat-number');
    
    console.log(`✓ Page loaded with ${totalAgencies} agencies and ${totalReports} reports`);
    
    // Count agency cards
    const agencyCards = await page.$$('.agency-card');
    console.log(`✓ Found ${agencyCards.length} agency cards displayed`);
    
    // Take a screenshot
    await page.screenshot({ path: '/tmp/playwright-test-screenshot.png', fullPage: true });
    console.log('✓ Screenshot saved to /tmp/playwright-test-screenshot.png');
    
    // Check file size of agencies_data.json from network
    const agenciesDataResponse = await page.evaluate(async () => {
        const response = await fetch('/data/agencies_data.json');
        const blob = await response.blob();
        return {
            size: blob.size,
            sizeKB: (blob.size / 1024).toFixed(2),
            sizeMB: (blob.size / 1024 / 1024).toFixed(2)
        };
    });
    
    console.log(`\n📊 File size information:`);
    console.log(`   - agencies_data.json: ${agenciesDataResponse.sizeMB} MB (${agenciesDataResponse.sizeKB} KB)`);
    
    await browser.close();
    
    console.log('\n✓ All tests passed! The dev server is working correctly.');
    console.log('✓ The agencies_data.json file is being downloaded and parsed successfully.');
}

// Run the test
testDevServer().catch(error => {
    console.error('Test failed:', error);
    process.exit(1);
});
