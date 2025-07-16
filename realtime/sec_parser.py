#Author: Taaj Stillitano
#Date Created: 2025-07-01
#Date Updated: 2025-07-01
#Description: This module contains functions to scrape HTML content from the TAR files
#loaded into the "bronze" directory. The HTML content is then parsed using BeautifulSoup
#and saved as JSON files in the "silver" directory.
#The JSON will have the following structure:
#[{"ticker": "AAPL", "cik": "0000320193", "filing_date": "2025-07-01", "content": "..."}, {...}]

import tarfile, json, re, tiktoken, os
from bs4 import BeautifulSoup
from pathlib import Path
from helper_functions.documents import get_tickers


MAX_TOKENS = 500
MODEL = "gpt-3.5-turbo"  # or whichever you want

def deep_get(d, key):
    """Recursively search dict for a key."""
    if isinstance(d, dict):
        if key in d:
            return d[key]
        for v in d.values():
            res = deep_get(v, key)
            if res is not None:
                return res
    return None

def extract_metadata(tar):
    for member in tar.getmembers():
        if "metadata.json" in member.name:
            f = tar.extractfile(member)
            if f:
                try:
                    metadata = json.load(f)
                    return {
                        "company_name": deep_get(metadata, "conformed-name") or None,
                        "filing_date": deep_get(metadata, "filing-date") or None,
                        "form_type": deep_get(metadata, "form-type") or deep_get(metadata, "type") or None,
                        "accession_number": deep_get(metadata, "accession-number") or None,
                        "cik": deep_get(metadata, "entity_cik") or deep_get(metadata, "cik") or None,
                    }
                except json.JSONDecodeError:
                    print("Warning: Could not parse metadata.json")
    # Return placeholders if no metadata.json found
    return {
        "company_name": None,
        "filing_date": None,
        "form_type": None,
        "accession_number": None,
        "cik": None,
    }

def extract_html_files(tar):
    files = []
    for member in tar.getmembers():
        if member.name.endswith((".htm", ".html")):
            f = tar.extractfile(member)
            if f:
                html = f.read().decode("utf-8", errors="ignore")
                files.append((member.name, html))
    return files

def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "head", "footer"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def chunk_text(text, max_tokens=MAX_TOKENS, model=MODEL):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = start + max_tokens
        chunk = encoding.decode(tokens[start:end])
        chunks.append(chunk)
        start = end
    return chunks

def sanitize_filename(s):
    return re.sub(r"[^a-zA-Z0-9\-]", "_", s) if s else "Unknown"

def process_tar(tar_path, output_dir):
    #get list of CIKs from database
    ciks = set(get_tickers().values())
    companies = set(get_tickers().keys())

    #get tar file name so if we encounter file with no metadata we can still save it
    tar_name = Path(tar_path).stem

    #get absolute path to silver folder
    data_folder_path = os.path.abspath(os.path.join(os.getcwd(), '..\\..\\data'))
    output_directory = data_folder_path+"\\silver"
    #check to see if it exist and if not then create it
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)


    with tarfile.open(tar_path, "r") as tar:
        metadata = extract_metadata(tar)
        html_files = extract_html_files(tar)

    if not html_files:
        print("No HTML files found in the TAR.")
        return

    for filename, html in html_files:
        text = clean_html(html)
        chunks = chunk_text(text)

        # Fill placeholders with fallback strings for filename
        company = sanitize_filename(metadata["company_name"]) if metadata["company_name"] else tar_name
        form_type = sanitize_filename(metadata["form_type"]) if metadata["form_type"] else Path(filename).stem
        filing_date = sanitize_filename(metadata["filing_date"]) if metadata["filing_date"] else "UnknownDate"
        cik = sanitize_filename(metadata["cik"]) if metadata["cik"] else "UnknownCIK"
        #try to convert cik to int if it is a string so that we can match it with the ciks in the 
        #database
        try:
            cik = str(int(cik))
        except:
            pass
        
        #only parse the data and save it if the CIK is in the list of S&P 500 companies
        if cik in ciks:
            output_filename = f"{company}_{form_type}_{filing_date}.json"

            data = []
            for i, chunk in enumerate(chunks):
                data.append({
                    "chunk_id": i,
                    "text": chunk,
                    **metadata,
                    "source_file": filename,
                })

            with open(output_dir / output_filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            print(f"Saved processed file: {output_filename}")
        else:
            print(f"{company} - {cik} not a part of SnP 500, skipping file: {filename}")