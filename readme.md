# OCR Data Extraction Script

This repository contains a Python script for extracting names and company information from images using NVIDIA's OCRNET API. The script uploads images to the NVIDIA API, processes them, extracts text, and classifies the text into names and companies. The results are saved to CSV files.

## Features

- Upload images to NVIDIA OCRNET API for OCR processing
- Extract and classify text into names and companies
- Save extracted data to CSV files

## Requirements

- Python 3.6+
- `requests` library
- `python-dotenv` library

## Installation

1. **Clone the repository:**

    ```sh
    git clone https://github.com/cdrguru/ocr-data-extraction.git
    cd ocr-data-extraction
    ```

2. **Create and activate a virtual environment:**

    ```sh
    python -m venv .venv
    ```

    - On **Windows**:

        ```sh
        .venv\Scripts\activate
        ```

    - On **macOS and Linux**:

        ```sh
        source .venv/bin/activate
        ```

3. **Install the required dependencies:**

    ```sh
    pip install -r requirements.txt
    ```

4. **Create a `.env` file** in the root directory of the project and add your NVIDIA API key:

    ```plaintext
    NGC_PERSONAL_API_KEY=your_nvidia_api_key_here
    ```

## Usage

1. **Prepare your images:**

    Place the images you want to process in a folder, for example, `images`.

2. **Run the script:**

    ```sh
    python script.py <image_folder> <output_folder>
    ```

    - `<image_folder>`: Path to the folder containing the images.
    - `<output_folder>`: Path to the folder where the output CSV files will be saved.

    Example:

    ```sh
    python script.py images output
    ```

## Script Details

### Functions

- **_upload_asset(input, description):**
  - Uploads an asset to the NVIDIA NVCF API.

- **classify_text(text):**
  - Classifies text as either a name or a company based on predefined keywords.

- **clean_text(text):**
  - Cleans the text by removing non-printable characters and excessive spaces.

- **parse_extracted_text(text):**
  - Parses the extracted text and organizes it into names and companies.

- **extract_and_parse_zip(zip_filename, output_folder):**
  - Extracts and parses the contents of a zip file.

- **main(image_folder, output_folder):**
  - Main function that orchestrates the processing of images, uploading to the API, extracting text, and saving to CSV.

## Example Directory Structure

```

your_project_directory/
│
├── .venv/
│
├── images/
│   ├── image1.jpg
│   ├── image2.png
│   └── ...
│
├── output/
│
├── .env
│
├── requirements.txt
│
└── script.py

```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any changes.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Acknowledgements

- [NVIDIA OCRNET API](https://developer.nvidia.com/ocrnet)
- [Python Requests Library](https://requests.readthedocs.io/en/latest/)
- [Python Dotenv Library](https://pypi.org/project/python-dotenv/)

```

Replace `cdrguru` in the clone command with your GitHub username or the URL of your repository. This `README.md` provides a comprehensive guide on how to set up and use your OCR data extraction script.
