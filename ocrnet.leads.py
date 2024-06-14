import os
import sys
import uuid
import zipfile
import requests
import csv
import json
import logging
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load NVIDIA API key from environment variables
NVIDIA_KEY = os.getenv("NGC_PERSONAL_API_KEY")

if not NVIDIA_KEY:
    logging.error("Error: NVIDIA API Key not found. Please check your .env file.")
    sys.exit(1)

# NVAI endpoint for the ocdrnet NIM
nvai_url = "https://ai.api.nvidia.com/v1/cv/nvidia/ocdrnet"

# API key (Ensure this is set appropriately in your environment)
header_auth = f"Bearer {NVIDIA_KEY}"

# Setup logging
logging.basicConfig(level=logging.INFO)

def _upload_asset(input, description):
    """
    Uploads an asset to the NVCF API.
    :param input: The binary asset to upload
    :param description: A description of the asset
    """
    assets_url = "https://api.nvcf.nvidia.com/v2/nvcf/assets"

    headers = {
        "Authorization": header_auth,
        "Content-Type": "application/json",
        "accept": "application/json",
    }

    s3_headers = {
        "x-amz-meta-nvcf-asset-description": description,
        "content-type": "image/jpeg",
    }

    payload = {"contentType": "image/jpeg", "description": description}

    response = requests.post(assets_url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()

    asset_url = response.json()["uploadUrl"]
    asset_id = response.json()["assetId"]

    response = requests.put(asset_url, data=input, headers=s3_headers, timeout=300)
    response.raise_for_status()
    return uuid.UUID(asset_id)

def classify_text(text):
    name_keywords = ["Mr.", "Ms.", "Dr.", "Prof.", "Name"]
    company_keywords = ["Inc.", "LLC", "Company", "Corp.", "Ltd.", "Solutions", "Services", "Technologies"]
    
    if any(keyword in text for keyword in name_keywords):
        return 'name'
    elif any(keyword in text for keyword in company_keywords):
        return 'company'
    else:
        return 'company' if any(char.isdigit() or not char.isalnum() for char in text) else 'name'

def clean_text(text):
    # Remove non-printable characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    # Remove excessive spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_extracted_text(text):
    lines = text.split('\n')
    extracted_data = []
    current_entry = {}

    for line in lines:
        line = clean_text(line)
        if not line:
            continue

        classification = classify_text(line)
        if classification == 'name':
            if 'first_name' in current_entry and 'last_name' in current_entry:
                extracted_data.append(current_entry)
                current_entry = {}
            name_parts = line.split()
            if len(name_parts) == 2:
                current_entry['first_name'] = name_parts[0]
                current_entry['last_name'] = name parts[1]
            else:
                current_entry['first_name'] = name_parts[0]
                current_entry['last_name'] = ' '.join(name_parts[1:])
        elif classification == 'company':
            current_entry['company'] = line

    if current_entry:
        extracted_data.append(current_entry)

    return extracted_data

def extract_and_parse_zip(zip_filename, output_folder):
    """Extracts and parses the contents of the zip file."""
    extracted_text = ""
    with zipfile.ZipFile(zip_filename, "r") as zip_ref:
        zip_ref.extractall(output_folder)
        for extracted_file in zip_ref.namelist():
            extracted_file_path = os.path.join(output_folder, extracted_file)
            if os.path.isfile(extracted_file_path) and extracted_file_path.endswith('.txt'):
                with open(extracted_file_path, "r", encoding='utf-8', errors='ignore') as file:
                    file_content = file.read()
                    logging.info(f"Extracted file content from {extracted_file_path}: {file_content[:100]}...")
                    extracted_text += file_content
    return extracted_text

def main(image_folder, output_folder):
    """Uploads images to the NVCF API, processes them with the OCR model,
    and saves the extracted data to CSV files in the output folder.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for image_name in os.listdir(image_folder):
        image_path = os.path.join(image_folder, image_name)

        # Ensure we are working with an image file
        if not os.path.isfile(image_path) or not image_name.lower().endswith(('.png', '.jpg', '.jpeg')):
            continue

        logging.info(f"Processing image: {image_name}")

        try:
            with open(image_path, "rb") as img_file:
                asset_id = _upload_asset(img_file, "Input Image")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error uploading image {image_name}: {e}")
            continue

        inputs = {"image": f"{asset_id}", "render_label": False}
        asset_list = f"{asset_id}"

        headers = {
            "Content-Type": "application/json",
            "NVCF-INPUT-ASSET-REFERENCES": asset_list,
            "NVCF-FUNCTION-ASSET-IDS": asset_list,
            "Authorization": header_auth,
        }

        try:
            response = requests.post(nvai_url, headers=headers, json=inputs, timeout=30)
            response.raise_for_status()

            # Save the response content as a zip file
            zip_filename = os.path.join(output_folder, f"{image_name}_output.zip")
            with open(zip_filename, "wb") as zip_file:
                zip_file.write(response.content)

            logging.info(f"Saved response to {zip_filename}")

            # Extract and parse the zip file
            extracted_text = extract_and_parse_zip(zip_filename, output_folder)
            logging.info(f"Extracted text from {zip_filename}: {extracted_text[:500]}...")

            # Parse the extracted text
            parsed_data = parse_extracted_text(extracted_text)
            logging.info(f"Parsed data: {parsed_data}")

            # Save to output CSV
            csv_filename = os.path.join(output_folder, f"{image_name}.csv")
            with open(csv_filename, "w", newline='', encoding='utf-8') as out_csv:
                writer = csv.DictWriter(out_csv, fieldnames=['first_name', 'last_name', 'company'])
                writer.writeheader()
                for result in parsed_data:
                    writer.writerow(result)

            logging.info(f"Saved CSV to {csv_filename}")

            # Clean up the zip file and extracted files
            os.remove(zip_filename)
            for extracted_file in os.listdir(output_folder):
                extracted_file_path = os.path.join(output_folder, extracted_file)
                if os.path.isfile(extracted_file_path):
                    os.remove(extracted_file_path)
                elif os.path.isdir(extracted_file_path):
                    os.rmdir(extracted_file_path)

        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err}")
        except requests.exceptions.RequestException as req_err:
            logging.error(f"Request error occurred: {req_err}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <image_folder> <output_folder>")
        sys.exit(1)

    IMAGE_FOLDER = sys.argv[1]
    OUTPUT_FOLDER = sys.argv[2]
    main(IMAGE_FOLDER, OUTPUT_FOLDER)
