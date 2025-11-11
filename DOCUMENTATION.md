# Contact Normalizer Documentation

## Overview

Contact Normalizer is a Python-based tool designed to clean, normalize, and validate contact information (phone numbers and email addresses) from CSV files. It can operate as both a web application and a command-line utility.

## Architecture

### Components

1. **`app.py`**: Flask web application with REST API endpoints and CLI interface
2. **`normalizer.py`**: Core normalization logic for emails and phone numbers
3. **`templates/index.html`**: Web interface for CSV upload and preview

## Features

### Email Normalization

The email normalization process handles:

- **Obfuscation fixes**: Converts "name at domain dot com" patterns to standard email format
- **Missing @ symbols**: Automatically inserts @ symbols based on known email providers
- **TLD typos**: Fixes common domain typos (e.g., "con" → "com", "ogr" → "org")
- **Formatting**: Removes extra spaces, normalizes dots, handles multiple @ symbols
- **Validation**: Regex-based validation to ensure proper email format

### Phone Normalization

The phone normalization process:

- **International format**: Converts phone numbers to E.164 format (+[country code][number])
- **Region handling**: Supports US/Canada (default +1) and international formats
- **Format cleanup**: Removes formatting characters (spaces, dashes, parentheses)
- **Extension removal**: Strips extension markers (ext, x) and keeps main number
- **Validation**: Ensures phone numbers are 8-15 digits (excluding country code)

## API Endpoints

### Web Interface

- `GET /`: Main web interface for CSV upload
- `POST /normalize_csv`: Process uploaded CSV file
- `GET /download_cleaned`: Download the normalized CSV file
- `GET /download_original`: Download the original uploaded CSV file
- `POST /send_emails`: Mock endpoint for sending emails to valid recipients

### REST API

- `POST /normalize`: Normalize individual phone/email pairs
  - Accepts JSON: `{"phone": "...", "email": "...", "default_region": "US"}`
  - Returns normalized values, validation status, and reason codes

## CSV Processing

### Input Format

The application automatically detects columns using fuzzy matching:

- **Name columns**: `firstname`, `namefirst`, `first`, `lastname`, `last`
- **Email columns**: `email`
- **Phone columns**: `phone`, `phonenumber`, `number`

### Output Format

The cleaned CSV includes:

- Original columns (first_name, last_name, email, phone)
- `email_normalized`: Normalized email address
- `email_valid`: Boolean validation result
- `email_reason`: Reason code (ok, empty, missing @, invalid pattern)
- `phone_normalized`: Normalized phone number in E.164 format
- `phone_valid`: Boolean validation result
- `phone_reason`: Reason code (ok, empty, invalid length)

## Command Line Interface

### Usage

```bash
python app.py --csv <file_path> --region <US|INTL>
```

### Arguments

- `--csv`: Path to CSV file to process (required for CLI mode)
- `--region`: Default region for phone normalization (default: US)

### Example

```bash
python app.py --csv contacts.csv --region US
```

Output: `contacts.cleaned.csv`

## Normalization Examples

### Email Examples

| Input | Output | Status |
|-------|--------|--------|
| `name at domain dot com` | `name@domain.com` | Valid |
| `user@example.con` | `user@example.com` | Valid |
| `user@@example.com` | `user@example.com` | Valid |
| `user example.com` | `user@example.com` | Valid (if provider detected) |

### Phone Examples

| Input | Output | Status |
|-------|--------|--------|
| `(555) 123-4567` | `+15551234567` | Valid |
| `555-123-4567` | `+15551234567` | Valid |
| `001234567890` | `+1234567890` | Valid |
| `5551234567` | `+15551234567` | Valid (US region) |

## Configuration

### Default Region

- **US**: Assumes 10-digit numbers are US/Canada (+1)
- **INTL**: No special assumptions, requires explicit country codes

### Session Management

The web application uses Flask sessions to store processed CSV data temporarily for download functionality.

## Error Handling

- Missing CSV files return 400 status with error message
- Invalid phone/email formats return validation status with reason codes
- Partial success scenarios return HTTP 207 (Multi-Status) for API endpoints

## Limitations

- Phone normalization uses simple heuristics and may not handle all international formats perfectly
- Email normalization relies on known providers for @ symbol insertion
- CSV preview is limited to 100 rows in the web interface
- Session-based storage may not persist across server restarts

## Future Enhancements

- Support for additional contact fields (addresses, names)
- Integration with email sending services
- Database storage for processed contacts
- Batch processing for large CSV files
- Additional phone number format support

