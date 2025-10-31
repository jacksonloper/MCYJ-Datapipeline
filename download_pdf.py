import requests
import base64
import urllib3
import os
import re
import argparse

def get_content_base_data(document_id):
    """
    POST request to fetch content base data for a given ContentDocumentId.
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Use same base endpoint as other functions; include the query params
    base_url = "https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/webruntime/api/apex/execute?language=en-US&asGuest=true&htmlEncode=false"

    payload = {
        "namespace": "",
        "classname": "@udd/01p8z0000009E4V",
        "method": "getContentBaseData",
        "isContinuation": False,
        "params": {
            "contentDocumentId": document_id,
            "actionName": "download"
        },
        "cacheable": False
    }

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://michildwelfarepubliclicensingsearch.michigan.gov',
        'Referer': 'https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/'
    }

    try:
        print(f"POST getContentBaseData for ContentDocumentId={document_id}")
        response = requests.post(
            base_url,
            json=payload,
            headers=headers,
            verify=False,
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"get_document_body failed for {document_id}: {e}")
        if 'response' in locals():
            try:
                print(f"Response content: {response.text}")
            except Exception:
                pass
        return None

# Note: I think we can do the same thing here using get_content_base_data
def download_michigan_pdf(document_id, document_agency=None, document_name=None, document_date=None, output_dir="./"):
    """
    Download a PDF from Michigan Child Welfare Public Licensing Search

    Args:
        document_id (str): The document ID (e.g., "0698z0000061FxYAAU")
        document_agency (str, optional): Name of the agency for filename
        document_name (str, optional): Name of the document for filename
        output_dir (str): Directory to save the PDF (default: current directory)

    Returns:
        str: Path to the downloaded file if successful, None if failed
    """

    # Disable SSL warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    try:
        # Make the request
        res = get_content_base_data(document_id=document_id)
        base64_data = res['returnValue']

        # Decode the PDF content
        pdf_content = base64.b64decode(base64_data)

        # Generate filename
        filename = generate_filename(document_id, document_agency, document_name, document_date)

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Full path for the file
        file_path = os.path.join(output_dir, filename)

        # Save the PDF
        with open(file_path, 'wb') as f:
            f.write(pdf_content)

        print(f"PDF downloaded successfully: {file_path}")
        print(f"File size: {len(pdf_content)} bytes")

        return file_path

    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        return None
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return None

def generate_filename(document_id, document_agency, document_name, document_date):
    """
    Generate a filename based on the provided parameters

    Args:
        document_id (str): The document ID
        document_agency (str): Agency name
        document_name (str): Document name
        document_date (str): Document date (not used in this version)

    Returns:
        str: Generated filename
    """
    # Clean up strings to be filesystem-safe
    def clean_string(s):
        if not s:
            return ""
        # Remove/replace problematic characters
        s = re.sub(r'[<>:"/\\|?*]', '_', s)
        # Remove extra whitespace
        s = re.sub(r'\s+', '_', s)
        # Remove leading/trailing underscores
        s = s.strip('_')
        return s

    # Build filename components
    parts = []

    if document_agency:
        parts.append(clean_string(document_agency))

    if document_name:
        parts.append(clean_string(document_name))

    if document_date:
        # Ensure the date is in YYYY-MM-DD format
        match = re.match(r'(\d{4})[-/](\d{2})[-/](\d{2})', str(document_date))
        # Raise error if month > 12
        if match:
            if int(match.group(2)) > 12:
                raise ValueError("Month in document date cannot be greater than 12")
            formatted_date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
            parts.append(formatted_date)
        else:
            # If not in correct format, skip or handle as needed
            raise ValueError("Document date must be in YYYY-MM-DD format")

    # Always include the document ID
    parts.append(clean_string(document_id))

    # Join parts with underscores
    filename = '_'.join(parts)

    # Ensure it ends with .pdf
    if not filename.lower().endswith('.pdf'):
        filename += '.pdf'

    return filename

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Michigan Child Welfare PDF by document ID.")
    parser.add_argument("document_id", help="The document ID (e.g., 0698z0000061FxYAAU)")
    parser.add_argument("--agency", dest="document_agency", help="Agency name for filename", default=None)
    parser.add_argument("--name", dest="document_name", help="Document name for filename", default=None)
    parser.add_argument("--output-dir", dest="output_dir", help="Directory to save the PDF", default="./")
    parser.add_argument("--date", dest="document_date", help="Document date for filename (YYYY-MM-DD)", default=None)

    args = parser.parse_args()

    download_michigan_pdf(
        document_id=args.document_id,
        document_agency=args.document_agency,
        document_name=args.document_name,
        document_date=args.document_date,
        output_dir=args.output_dir
    )