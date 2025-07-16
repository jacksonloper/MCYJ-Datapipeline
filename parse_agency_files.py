    import argparse
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    import time

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Child Welfare Licensing agency PDFs from Michigan's public licensing search.")
    parser.add_argument("--driver-path", dest="driver_path", help="Path to the ChromeDriver executable", default=None)
    parser.add_argument("--agency-url", dest="agency_url", help="URL of the agency page to parse", required=True)
    parser.add_argument("--output-dir", dest="output_dir", help="Directory to save the CSV file", default="./")

    args = parser.parse_args()

    # Initialize the WebDriver
    service = Service(args.driver_path)
    driver = webdriver.Chrome(service=service)
    driver.get(url)
    time.sleep(5)

    # Get the document agency name
    document_agency_element = driver.find_elements(By.XPATH, "//lightning-layout-item[1]/slot/div[1]/div")
    document_agency = "_".join([element.text.strip().replace(" ", "_").replace("/", "_") for element in document_agency_element]) if document_agency_element else "Unknown_Agency"

    print(document_agency)

    # Locate all rows within the table
    table_rows = driver.find_elements(By.XPATH, "//lightning-datatable/div[2]/div/div/table/tbody/tr")

