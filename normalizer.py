import re
import unicodedata


_TLD_FIXES = {
    "con": "com",
    "c0m": "com",
    "cim": "com",
    "cpm": "com",
    "ogr": "org",
    "ntt": "net",
}

_KNOWN_PROVIDERS = [
    "gmail", "googlemail", "yahoo", "hotmail", "outlook", "icloud",
    "proton", "protonmail", "aol", "msn", "live", "me", "ymail",
]

_COMMON_TLDS = [
    "com", "org", "net", "edu", "gov", "io", "ai", "app", "dev",
    "co", "us", "uk", "ca", "de", "fr", "it", "nl", "es", "br",
]

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _compact_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def normalize_phone(raw: str, default_region: str = "US"):
    s = str(raw or "")
    if not s.strip():
        return "", False, "empty"

    s = _strip_accents(s)
    s = s.replace("–", "-").replace("—", "-").replace("−", "-")

    # Remove common extension markers (keep main number only)
    s = re.split(r"(?i)(ext\.?|x)\s*\d+", s)[0]

    # Convert leading 00 to + (international format)
    s = re.sub(r"^\s*00", "+", s)

    # Keep only digits and plus
    kept = []
    for i, ch in enumerate(s):
        if ch.isdigit():
            kept.append(ch)
        elif ch == "+":
            # keep only one leading plus
            if not kept:
                kept.append(ch)
            # else ignore
        # ignore all other characters (spaces, dashes, parentheses, etc.)

    cleaned = "".join(kept)

    # Remove any stray plus not at the beginning
    if cleaned.count("+") > 1:
        first_plus = cleaned.find("+")
        cleaned = "+" + cleaned[first_plus + 1:].replace("+", "")

    # Separate sign and digits
    if cleaned.startswith("+"):
        sign = "+"
        digits = re.sub(r"\D", "", cleaned[1:])
    else:
        sign = ""
        digits = re.sub(r"\D", "", cleaned)

    # Apply simple region defaults
    normalized = None
    reason = ""

    if not sign:
        # No explicit country code
        if default_region.upper() in {"US", "CA"}:
            if len(digits) == 10:
                normalized = "+1" + digits
            elif len(digits) == 11 and digits.startswith("1"):
                normalized = "+1" + digits[1:]
        # Fallback for other plausible international lengths
        if normalized is None and 8 <= len(digits) <= 15:
            normalized = "+" + digits
    else:
        normalized = "+" + digits

    # Final validation on length
    if not normalized:
        return "", False, f"unusable length {len(digits)}"

    final_digits = normalized[1:]
    if not (8 <= len(final_digits) <= 15):
        return "", False, f"invalid length {len(final_digits)}"

    return normalized, True, "ok"


def _apply_email_obfuscation_fixes(s: str) -> str:
    # Normalize common obfuscations like "name at domain dot com"
    s = s.lower()
    s = _strip_accents(s)
    s = s.replace("＠", "@")

    # Replace [at], (at), {at}, spaces around, etc.
    s = re.sub(r"\s*\[?\(?\{?\s*at\s*\}?\)?\]?\s*", "@", s, flags=re.I)
    # Replace [dot], (dot), {dot}
    s = re.sub(r"\s*\[?\(?\{?\s*dot\s*\}?\)?\]?\s*", ".", s, flags=re.I)
    # Replace multiple spaces and remove any remaining spaces
    s = _compact_spaces(s).replace(" ", "")
    # Commas and semicolons often used instead of dots
    s = s.replace(",", ".").replace(";", ".")
    # Remove duplicate consecutive dots
    s = re.sub(r"\.+", ".", s)
    return s


def _insert_missing_at(s: str) -> str:
    # If missing '@', try to infer by known providers in the string
    if "@" in s:
        return s
    for provider in _KNOWN_PROVIDERS:
        idx = s.find(provider)
        if idx > 0:
            return s[:idx] + "@" + s[idx:]
    return s


def _fix_domain_tld(domain: str) -> str:
    # Fix trailing TLD typos like example.con -> example.com
    parts = domain.rsplit(".", 1)
    if len(parts) == 2:
        host, tld = parts
        tld_fixed = _TLD_FIXES.get(tld, tld)
        return f"{host}.{tld_fixed}"

    # If no dot, attempt to split by known TLD suffix
    for tld in sorted(_COMMON_TLDS, key=len, reverse=True):
        if domain.endswith(tld) and len(domain) > len(tld):
            host = domain[: -len(tld)]
            # Avoid extra dot if host already ends with dot
            host = host[:-1] if host.endswith(".") else host
            return f"{host}.{tld}"

    return domain


def normalize_email(raw: str):
    s = str(raw or "")
    if not s.strip():
        return "", False, "empty"

    s = _apply_email_obfuscation_fixes(s)

    # If there are multiple @, keep the first and drop the rest
    if s.count("@") > 1:
        first, rest = s.split("@", 1)
        rest = rest.replace("@", "")
        s = first + "@" + rest

    # If missing '@', try to insert heuristically
    if "@" not in s:
        s = _insert_missing_at(s)

    # Now try to split local and domain; if still no '@', fail early
    if "@" not in s:
        return "", False, "missing @"

    local, domain = s.split("@", 1)

    # Clean leading/trailing dots
    local = local.strip(".")
    domain = domain.strip(".")

    # Collapse duplicate dots inside local and domain
    local = re.sub(r"\.+", ".", local)
    domain = re.sub(r"\.+", ".", domain)

    # Ensure domain has a dot; if not, try to infer
    if "." not in domain:
        domain = _fix_domain_tld(domain)

    # Apply final TLD typo fixes
    domain = _fix_domain_tld(domain)

    candidate = f"{local}@{domain}".lower()

    # Final regex validation
    if not _EMAIL_RE.match(candidate):
        return "", False, "invalid pattern"

    return candidate, True, "ok"

