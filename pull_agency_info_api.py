import csv
import requests
import json
import urllib.parse
import urllib3

def get_agency_details(record_id):
    """
    GET request with URL parameters directly to the API endpoint
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    base_url = "https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/webruntime/api/apex/execute"

    # Build the exact URL from your example
    params = {
        "cacheable": "true",
        "classname": "@udd/01p8z0000009E4V",
        "isContinuation": "false",
        "method": "getAgenciesDetail",
        "namespace": "",
        "params": json.dumps({"recordId": record_id}),
        "language": "en-US",
        "asGuest": "true",
        "htmlEncode": "false"
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/'
    }

    try:
        print("Method 1: GET request with URL parameters")
        response = requests.get(base_url, params=params, headers=headers, verify=False, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Method 1 failed: {e}")
        return None

# Get the files
def get_content_details_method(record_id):
    """
    POST with JSON payload directly to the API endpoint
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    base_url = "https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/webruntime/api/apex/execute"

    # JSON payload
    payload = {
        "namespace": "",
        "classname": "@udd/01p8z0000009E4V",
        "method": "getContentDetails",
        "isContinuation": False,
        "params": {
            "recordId": record_id
        },
        "cacheable": False
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://michildwelfarepubliclicensingsearch.michigan.gov',
        'Referer': 'https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/'
    }

    try:
        print("POST with JSON payload directly to the API endpoint")
        print(f"Payload: {json.dumps(payload, indent=2)}")

        response = requests.post(
            base_url,
            json=payload,
            headers=headers,
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"POST with JSON payload directly to the API endpoint failed: {e}")
        if 'response' in locals():
            print(f"Response content: {response.text}")
        return None

# Test the functions
if __name__ == "__main__":
    keep_cols = ['FileExtension', 'CreatedDate', 'Title', 'ContentBodyId', 'Id', 'ContentDocumentId']
    record_id = "a0i8z0000006SelAAE"

    result = get_agency_details(record_id)
    pdf_results = get_content_details_method(record_id)

    if result:
        print("Saving agency details:")
        print(json.dumps(result, indent=2))
        with open(f"{record_id}_agency_details.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Agency details saved to {record_id}_agency_details.json")
    else:
        print("Failed to retrieve agency details.")

    if pdf_results:
        print("PDF Content Details:")
        print(json.dumps(pdf_results, indent=2))
        # Save full JSON response to file
        json_file = f"{record_id}_pdf_content_details.json"
        with open(json_file, "w", encoding="utf-8") as jf:
            json.dump(pdf_results, jf, indent=2, ensure_ascii=False)
        print(f"Full JSON results written to {json_file}")

        # print(pdf_results.keys())
        # Write top-level keys/values to CSV
        csv_file = "pdf_content_details.csv"
        with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            # Write the header
            writer.writerow(keep_cols)
            for p in pdf_results.get('returnValue', {}).get('contentVersionRes', []):
                row_data = []
                for k,v in p.items():
                    if k in keep_cols:
                        row_data.append(v)
                # print(row_data)
                writer.writerow(row_data)

        print(f"Top-level JSON results written to {csv_file}")
    else:
        print("Failed to retrieve PDF content details.")