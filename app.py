from flask import Flask, request, jsonify, render_template, send_file, session
from normalizer import normalize_phone, normalize_email
import argparse
import csv
import os
import re
import io
import base64


def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)  # For session management

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/normalize")
    def normalize():
        # Accept both JSON and form submissions
        if request.is_json:
            payload = request.get_json(silent=True) or {}
            raw_phone = payload.get("phone", "")
            raw_email = payload.get("email", "")
            default_region = payload.get("default_region", "US")
        else:
            raw_phone = request.form.get("phone", "")
            raw_email = request.form.get("email", "")
            default_region = request.form.get("default_region", "US")

        phone_value, phone_ok, phone_reason = normalize_phone(raw_phone, default_region)
        email_value, email_ok, email_reason = normalize_email(raw_email)

        response = {
            "input": {
                "phone": raw_phone,
                "email": raw_email,
                "default_region": default_region,
            },
            "normalized": {
                "phone": phone_value,
                "email": email_value,
            },
            "valid": {
                "phone": phone_ok,
                "email": email_ok,
            },
            "reasons": {
                "phone": phone_reason,
                "email": email_reason,
            },
        }

        # For form submissions, render a simple result view
        if not request.is_json:
            return render_template(
                "index.html",
                result=response,
                phone_ok=phone_ok,
                email_ok=email_ok,
            )

        # For JSON, return structured output
        http_status = 200 if phone_ok and email_ok else 207  # Multi-Status for partial success
        return jsonify(response), http_status

    @app.post("/normalize_csv")
    def normalize_csv():
        # Handle CSV uploads via form and return a cleaned CSV for download
        uploaded = request.files.get("csv_file")
        default_region = request.form.get("default_region", "US")
        preview_only = request.form.get("preview_only", "false") == "true"

        if not uploaded or uploaded.filename == "":
            # Re-render with an error for missing file
            return render_template("index.html", upload_error="Please choose a CSV file."), 400

        # Read the uploaded bytes and decode as UTF-8 (be tolerant of errors/BOM)
        raw_bytes = uploaded.read()
        try:
            text = raw_bytes.decode("utf-8-sig", errors="replace")
        except Exception:
            text = raw_bytes.decode("utf-8", errors="replace")

        def _key(s: str) -> str:
            return re.sub(r"[^a-z0-9]", "", (s or "").strip().lower())

        # Read original CSV for preview
        in_buf = io.StringIO(text)
        reader = csv.DictReader(in_buf)
        original_headers = reader.fieldnames or []
        original_rows = list(reader)

        # Reset buffer for processing
        in_buf = io.StringIO(text)
        reader = csv.DictReader(in_buf)
        headers_norm = {_key(h): h for h in (reader.fieldnames or [])}

        last_col = headers_norm.get("lastname") or headers_norm.get("last")
        first_col = (
            headers_norm.get("namefirst")
            or headers_norm.get("firstname")
            or headers_norm.get("first")
        )
        email_col = headers_norm.get("email")
        phone_col = (
            headers_norm.get("number")
            or headers_norm.get("phonenumber")
            or headers_norm.get("phone")
        )

        out_fields = [
            first_col or "first_name",
            last_col or "last_name",
            email_col or "email",
            phone_col or "phone",
            "email_normalized",
            "email_valid",
            "email_reason",
            "phone_normalized",
            "phone_valid",
            "phone_reason",
        ]

        out_buf = io.StringIO(newline="")
        writer = csv.DictWriter(out_buf, fieldnames=out_fields)
        writer.writeheader()

        output_rows = []
        for row in reader:
            raw_email = row.get(email_col, "") if email_col else ""
            raw_phone = row.get(phone_col, "") if phone_col else ""

            email_value, email_ok, email_reason = normalize_email(raw_email)
            phone_value, phone_ok, phone_reason = normalize_phone(raw_phone, default_region)

            out_row = dict(row)
            out_row.setdefault(first_col or "first_name", row.get(first_col, "") if first_col else "")
            out_row.setdefault(last_col or "last_name", row.get(last_col, "") if last_col else "")
            out_row.setdefault(email_col or "email", raw_email)
            out_row.setdefault(phone_col or "phone", raw_phone)
            out_row["email_normalized"] = email_value
            out_row["email_valid"] = str(bool(email_ok))
            out_row["email_reason"] = email_reason
            out_row["phone_normalized"] = phone_value
            out_row["phone_valid"] = str(bool(phone_ok))
            out_row["phone_reason"] = phone_reason

            writer.writerow({k: out_row.get(k, "") for k in out_fields})
            output_rows.append({k: out_row.get(k, "") for k in out_fields})

        csv_text = out_buf.getvalue()
        out_bytes = csv_text.encode("utf-8")
        base, _ = os.path.splitext(uploaded.filename or "contacts.csv")
        download_name = f"{base}.cleaned.csv"

        # Store in session for download
        session['cleaned_csv'] = base64.b64encode(out_bytes).decode('utf-8')
        session['cleaned_filename'] = download_name
        session['original_csv'] = base64.b64encode(text.encode('utf-8')).decode('utf-8')
        session['original_filename'] = uploaded.filename or "contacts.csv"

        # If preview only, return template with data
        if preview_only:
            return render_template(
                "index.html",
                csv_preview={
                    "headers": original_headers,
                    "rows": original_rows[:100],  # Limit preview to 100 rows
                    "total_rows": len(original_rows)
                },
                csv_output={
                    "headers": out_fields,
                    "rows": output_rows[:100],  # Limit preview to 100 rows
                    "total_rows": len(output_rows)
                }
            )

        return send_file(
            io.BytesIO(out_bytes),
            mimetype="text/csv",
            as_attachment=True,
            download_name=download_name,
        )

    @app.get("/download_original")
    def download_original():
        csv_data = base64.b64decode(session.get('original_csv', ''))
        filename = session.get('original_filename', 'contacts.csv')
        return send_file(
            io.BytesIO(csv_data),
            mimetype="text/csv",
            as_attachment=True,
            download_name=filename,
        )

    @app.get("/download_cleaned")
    def download_cleaned():
        csv_data = base64.b64decode(session.get('cleaned_csv', ''))
        filename = session.get('cleaned_filename', 'contacts.cleaned.csv')
        return send_file(
            io.BytesIO(csv_data),
            mimetype="text/csv",
            as_attachment=True,
            download_name=filename,
        )

    @app.post("/send_emails")
    def send_emails():
        # Mock email sending endpoint
        csv_data = base64.b64decode(session.get('cleaned_csv', ''))
        text = csv_data.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        
        emails_sent = 0
        for row in reader:
            email = row.get("email_normalized", "")
            if email and row.get("email_valid", "").lower() == "true":
                emails_sent += 1
        
        return jsonify({
            "success": True,
            "message": f"Mock: Sent emails to {emails_sent} recipients",
            "count": emails_sent
        })

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Contact normalizer service/CLI")
    parser.add_argument(
        "--csv",
        dest="csv_path",
        help="Path to a CSV file to normalize (runs as CLI and exits).",
    )
    parser.add_argument(
        "--region",
        dest="default_region",
        default="US",
        help="Default region for phone normalization (e.g., US, INTL).",
    )
    args = parser.parse_args()

    if args.csv_path:
        # CLI mode: normalize a CSV and write an output alongside the input
        in_path = args.csv_path
        if not os.path.exists(in_path):
            raise SystemExit(f"CSV not found: {in_path}")

        base, ext = os.path.splitext(in_path)
        out_path = f"{base}.cleaned.csv"

        def _key(s: str) -> str:
            # normalize header names for fuzzy matching
            return re.sub(r"[^a-z0-9]", "", (s or "").strip().lower())

        with open(in_path, newline="", encoding="utf-8") as f_in:
            reader = csv.DictReader(f_in)
            headers_norm = {_key(h): h for h in reader.fieldnames or []}

            # Try to find expected columns by fuzzy key
            last_col = headers_norm.get("lastname") or headers_norm.get("last")
            first_col = headers_norm.get("namefirst") or headers_norm.get("firstname") or headers_norm.get("first")
            email_col = headers_norm.get("email")
            phone_col = headers_norm.get("number") or headers_norm.get("phonenumber") or headers_norm.get("phone")

            # Prepare writer with explicit columns
            out_fields = [
                first_col or "first_name",
                last_col or "last_name",
                email_col or "email",
                phone_col or "phone",
                "email_normalized",
                "email_valid",
                "email_reason",
                "phone_normalized",
                "phone_valid",
                "phone_reason",
            ]

            with open(out_path, "w", newline="", encoding="utf-8") as f_out:
                writer = csv.DictWriter(f_out, fieldnames=out_fields)
                writer.writeheader()

                for row in reader:
                    raw_email = row.get(email_col, "") if email_col else ""
                    raw_phone = row.get(phone_col, "") if phone_col else ""

                    email_value, email_ok, email_reason = normalize_email(raw_email)
                    phone_value, phone_ok, phone_reason = normalize_phone(raw_phone, args.default_region)

                    out_row = dict(row)  # keep original data
                    out_row.setdefault(first_col or "first_name", row.get(first_col, "") if first_col else "")
                    out_row.setdefault(last_col or "last_name", row.get(last_col, "") if last_col else "")
                    out_row.setdefault(email_col or "email", raw_email)
                    out_row.setdefault(phone_col or "phone", raw_phone)
                    out_row["email_normalized"] = email_value
                    out_row["email_valid"] = str(bool(email_ok))
                    out_row["email_reason"] = email_reason
                    out_row["phone_normalized"] = phone_value
                    out_row["phone_valid"] = str(bool(phone_ok))
                    out_row["phone_reason"] = phone_reason

                    # Only keep known fields in output
                    writer.writerow({k: out_row.get(k, "") for k in out_fields})

        print(f"Wrote normalized CSV: {out_path}")
    else:
        app = create_app()
        app.run(host="0.0.0.0", port=5001, debug=True)
