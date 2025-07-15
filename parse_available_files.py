# Selenium is used for web automation and scraping
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import ElementClickInterceptedException
# Time utilities for delays and timestamp handling
import argparse
import time
from time import sleep
# Date and time parsing
from datetime import datetime
# File and path operations
from pathlib import Path
import os
import glob

import csv
import re

## First get the agency URLs (and ids)
#def get_agency_information():
def get_agency_information(driver):
    """
    Extracts agency information from a web page using Selenium.

    Args:
        driver (webdriver): The Selenium WebDriver instance.

    Returns:
        list: A list of dictionaries containing agency information.
    """
    driver.get("https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/")
    time.sleep(5) # Wait for the page to fully load (longer than usual due to dynamic content)
    # Prepare an empty list to store all agency-specific URLs found across pages

    sub_urls = []
    table_header = []
    table_data = []
    header_elements = driver.find_elements(By.XPATH, "//lightning-datatable//table/thead/tr/th")
    # Clean up header text by removing "Sort by:" and "Sorted: None"
    for i, header in enumerate(header_elements):
        text = header.text.strip()
        text = text.replace("Sort by:", "").replace("Sorted: None", "").replace("\n", " ").strip()
        table_header.append(text)

    while True:
        # Find the license number rows:
        # Change this to tr OR th
        table_rows = driver.find_elements(By.XPATH, "//lightning-datatable//table/tbody/tr")
        for row in table_rows:
            # Find all columns (td elements) in the row
            row_data = []
            columns = row.find_elements(By.XPATH, "./td | ./th")
            for col in columns:
                row_data.append(col.text.strip())
            table_data.append(row_data)

        for row in table_rows:
            link_elements = row.find_elements(By.XPATH, ".//lightning-formatted-url/a")
            for link in link_elements:
                href = link.get_attribute('href')
                if href:
                    sub_urls.append(href)

        try:
            # Try to locate and click the "Next" page button to load the next page of results
            next_button = driver.find_element(By.XPATH, "//lightning-button-icon[3]/button/lightning-primitive-icon")
            next_button.click()
        except ElementClickInterceptedException:
            # If the click fails (e.g., no more pages or overlay blocking it), stop the loop
            print("No more pages available.")
            break
    return sub_urls, table_header, table_data

def write_agency_information_to_csv(sub_urls, table_header, table_data, output_dir):
    """
    Writes the agency information to a CSV file.

    Args:
        sub_urls (list): List of agency URLs.
        table_header (list): List of table headers.
        table_data (list): List of table data rows.
        output_dir (str): Directory where the CSV file will be saved.
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Define the output CSV file path
    # Add date to the filename to avoid overwriting
    date_str = datetime.now().strftime("%Y%m%d")
    csv_filename = f"agency_information_{date_str}.csv"
    csv_file_path = os.path.join(output_dir, csv_filename)

    # Write to CSV file
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
       writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
       writer.writerow(table_header)  # Write header
       writer.writerows(table_data)  # Write data rows

    print(f"Agency information written to {csv_file_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Child Welfare Licensing agency PDFs from Michigan's public licensing search.")
    parser.add_argument("--driver-path", dest="driver_path", help="Path to the ChromeDriver executable", default=None)
    parser.add_argument("--output-dir", dest="output_dir", help="Directory to save the CSV file", default="./")

    args = parser.parse_args()

    # Initialize the WebDriver
    service = Service(args.driver_path)
    driver = webdriver.Chrome(service=service)

    try:
        sub_urls, table_header, table_data = get_agency_information(driver)
        write_agency_information_to_csv(sub_urls, table_header, table_data, args.output_dir)
    finally:
        driver.quit()  # Ensure the driver is closed after use