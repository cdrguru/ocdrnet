import os
import requests
import base64
import csv
import logging
from dotenv import load_dotenv
from PIL import Image
import io
import re

# Load environment variables from .env file
load_dotenv()

# Load API keys from environment variables
NVIDIA_KEY = os.getenv("NVIDIA_NGC_PERSONAL_API_KEY")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='processing.log', filemode='w')

# Print the loaded API key for debugging purposes
logging.info(f"NVIDIA API Key: {NVIDIA_KEY}")

if not NVIDIA_KEY:
    raise ValueError("NVIDIA API Key not found. Please set NVIDIA_NGC_PERSONAL_API_KEY in the .env file.")

# NVIDIA API setup
INVOKE_URL = "https://ai.api.nvidia.com/v1/vlm/microsoft/phi-3-vision-128k-instruct"
HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {NVIDIA_KEY}"
}

def resize_image(image_path, max_size_kb=180):
    """Resize the image to fit within the size limit."""
    try:
        img = Image.open(image_path)
        img_format = img.format

        # Reduce the image size in a loop until it fits within the size limit
        while True:
            with io.BytesIO() as buffer:
                img.save(buffer, format=img_format)
                size_kb = len(buffer.getvalue()) / 1024
                if size_kb <= max_size_kb:
                    buffer.seek(0)  # Reset buffer position to the beginning
                    return buffer.getvalue()
                # Resize image by reducing dimensions
                img = img.resize((int(img.width * 0.9), int(img.height * 0.9)), Image.Resampling.LANCZOS)
    except Exception as e:
        logging.error(f"Error resizing image {image_path}: {e}")
        return None

def encode_image(image_path):
    """Encode the image to base64 and check its size."""
    img_data = resize_image(image_path)
    if img_data:
        image_b64 = base64.b64encode(img_data).decode()
        return image_b64
    logging.error(f"Failed to encode image {image_path}")
    return None

def analyze_image(image_b64):
    """Send the image for analysis to NVIDIA API."""
    payload = {
        "messages": [
            {
                "role": "user",
                "content": f'Please extract the names and their corresponding company names from the image. Each name is followed by the company name. Ignore any miscellaneous text such as "Attendee List", "sessions", etc. Ensure that each extracted pair is in the format "Name, Company". <img src="data:image/jpg;base64,{image_b64}" />'
            }
        ],
        "max_tokens": 1024,  # Increased max_tokens to 1024
        "temperature": 1.00,
        "top_p": 0.70
    }

    response = requests.post(INVOKE_URL, headers=HEADERS, json=payload)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 401:
        logging.error("Unauthorized. Please check your NVIDIA API key.")
        logging.error(f"Response: {response.json()}")
        return None
    else:
        logging.error(f"Error: {response.status_code}")
        logging.error(f"Response: {response.json()}")
        return None

def extract_data(result):
    """Extract names and companies from the result."""
    if "choices" in result:
        content = result["choices"][0]["message"]["content"]
        lines = content.split('\n')
        extracted_data = []

        name_company_pattern = re.compile(r"(.+?),\s*(.+)")

        for line in lines:
            line = line.strip()
            if line:
                match = name_company_pattern.match(line)
                if match:
                    name = match.group(1).strip()
                    company = match.group(2).strip()
                    extracted_data.append((name, company))
        return extracted_data
    return []

def save_to_csv(data, file_path):
    """Save extracted data to a CSV file."""
    try:
        with open(file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Name", "Company"])
            for row in data:
                writer.writerow(row)
        logging.info(f"Data saved to {file_path}")
    except IOError as e:
        logging.error(f"Error saving to CSV: {e}")

def main(input_folder, output_csv):
    """Main function to execute the workflow."""
    extracted_data = []
    for filename in os.listdir(input_folder):
        if filename.endswith(".jpg"):
            image_path = os.path.join(input_folder, filename)
            logging.info(f"Processing {image_path}")
            image_b64 = encode_image(image_path)
            if image_b64:
                result = analyze_image(image_b64)
                if result:
                    data = extract_data(result)
                    extracted_data.extend(data)
                    logging.info(f"Successfully processed {image_path}")
                else:
                    logging.error(f"Failed to get the result for {image_path}")
            else:
                logging.error(f"Failed to encode {image_path}")
    save_to_csv(extracted_data, output_csv)

if __name__ == "__main__":
    INPUT_FOLDER = "input/"
    OUTPUT_CSV = "extracted_data.csv"
    main(INPUT_FOLDER, OUTPUT_CSV)
