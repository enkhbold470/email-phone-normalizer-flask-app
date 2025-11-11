# Contact Normalizer

A Flask web application and CLI tool for normalizing and validating phone numbers and email addresses from CSV files.

## Features

- **Email Normalization**: Fixes common typos, obfuscations, and formatting issues in email addresses
- **Phone Normalization**: Converts phone numbers to international format (E.164) with country code prefixes
- **CSV Processing**: Batch process contact data from CSV files with automatic column detection
- **Web Interface**: Upload CSV files, preview cleaned data, and download normalized results
- **CLI Mode**: Process CSV files from the command line
- **Validation**: Validates normalized emails and phone numbers with detailed reason codes

## Quick Start

### Web Application

```bash
python app.py
```

Access the web interface at `http://localhost:5001`

### CLI Mode

```bash
python app.py --csv contacts.csv --region US
```

This will generate a `contacts.cleaned.csv` file with normalized data.

## Requirements

- Python 3.x
- Flask

## Usage

1. Upload a CSV file containing contact information (names, emails, phone numbers)
2. The application automatically detects email and phone columns
3. Preview the cleaned data in the web interface
4. Download the normalized CSV file with validation results

