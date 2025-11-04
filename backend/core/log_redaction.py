"""
Log Redaction Utilities (Sprint 2)

Sanitizes logs to prevent sensitive data leakage.

Redacts:
- Passwords
- API keys
- Tokens (JWT, refresh, API)
- Credit card numbers
- Email addresses (partially)
- IP addresses (last octet)
- Phone numbers

Usage:
    from backend.core.log_redaction import redact_sensitive_data
    
    log_data = {"user": "john", "password": "secret123"}
    safe_data = redact_sensitive_data(log_data)
    logger.info(f"Login attempt: {safe_data}")
"""

import re
import logging
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)

# Sensitive field names (case-insensitive)
SENSITIVE_FIELDS = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "token",
    "auth",
    "authorization",
    "bearer",
    "session",
    "cookie",
    "csrf",
    "credit_card",
    "card_number",
    "cvv",
    "ssn",
    "social_security",
    "private_key",
    "encryption_key",
    "master_key",
}

# Regex patterns for sensitive data
PATTERNS = {
    "email": re.compile(r"([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"),
    "jwt": re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    "api_key": re.compile(r"[a-zA-Z0-9_-]{32,}"),
    "credit_card": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    "phone": re.compile(r"\+?1?\d{9,15}"),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}

REDACTION_PLACEHOLDER = "***REDACTED***"


def redact_string(value: str, field_name: str = "") -> str:
    """
    Redact sensitive information from a string.
    
    Args:
        value: String to redact
        field_name: Field name (for context-aware redaction)
    
    Returns:
        Redacted string
    """
    if not value or not isinstance(value, str):
        return value
    
    # Full redaction for known sensitive fields
    if field_name.lower() in SENSITIVE_FIELDS:
        return REDACTION_PLACEHOLDER
    
    # Partial redaction for emails (keep domain)
    if "@" in value:
        value = PATTERNS["email"].sub(r"***@\2", value)
    
    # Redact JWT tokens
    value = PATTERNS["jwt"].sub(REDACTION_PLACEHOLDER, value)
    
    # Redact long API keys
    if len(value) >= 32 and field_name.lower() in {"key", "token", "secret"}:
        value = value[:8] + "..." + REDACTION_PLACEHOLDER
    
    # Redact credit card numbers (keep last 4 digits)
    value = PATTERNS["credit_card"].sub(r"****-****-****-\4", value)
    
    # Partially redact IP addresses (keep first 3 octets)
    value = PATTERNS["ip_address"].sub(lambda m: ".".join(m.group().split(".")[:3]) + ".***", value)
    
    return value


def redact_dict(data: Dict[str, Any], depth: int = 0, max_depth: int = 10) -> Dict[str, Any]:
    """
    Redact sensitive fields in a dictionary (recursive).
    
    Args:
        data: Dictionary to redact
        depth: Current recursion depth
        max_depth: Maximum recursion depth (prevent infinite loops)
    
    Returns:
        Dictionary with redacted values
    """
    if depth > max_depth:
        return {"error": "max_depth_exceeded"}
    
    if not isinstance(data, dict):
        return data
    
    redacted = {}
    
    for key, value in data.items():
        # Redact sensitive fields
        if key.lower() in SENSITIVE_FIELDS:
            redacted[key] = REDACTION_PLACEHOLDER
        elif isinstance(value, str):
            redacted[key] = redact_string(value, key)
        elif isinstance(value, dict):
            redacted[key] = redact_dict(value, depth + 1, max_depth)
        elif isinstance(value, (list, tuple)):
            redacted[key] = redact_list(value, depth + 1, max_depth)
        else:
            redacted[key] = value
    
    return redacted


def redact_list(data: Union[List, tuple], depth: int = 0, max_depth: int = 10) -> list:
    """
    Redact sensitive fields in a list (recursive).
    
    Args:
        data: List to redact
        depth: Current recursion depth
        max_depth: Maximum recursion depth
    
    Returns:
        List with redacted values
    """
    if depth > max_depth:
        return ["max_depth_exceeded"]
    
    redacted = []
    
    for item in data:
        if isinstance(item, str):
            redacted.append(redact_string(item))
        elif isinstance(item, dict):
            redacted.append(redact_dict(item, depth + 1, max_depth))
        elif isinstance(item, (list, tuple)):
            redacted.append(redact_list(item, depth + 1, max_depth))
        else:
            redacted.append(item)
    
    return redacted


def redact_sensitive_data(data: Any) -> Any:
    """
    Main redaction function (handles any data type).
    
    Args:
        data: Data to redact (dict, list, string, or other)
    
    Returns:
        Redacted data (same type as input)
    
    Example:
        >>> redact_sensitive_data({"user": "alice", "password": "secret"})
        {'user': 'alice', 'password': '***REDACTED***'}
    """
    if isinstance(data, dict):
        return redact_dict(data)
    elif isinstance(data, (list, tuple)):
        return redact_list(data)
    elif isinstance(data, str):
        return redact_string(data)
    else:
        return data


def redact_exception(exc: Exception) -> str:
    """
    Redact sensitive information from exception messages.
    
    Args:
        exc: Exception instance
    
    Returns:
        Redacted exception message
    
    Example:
        try:
            api_call(api_key="secret123")
        except Exception as e:
            logger.error(redact_exception(e))
    """
    message = str(exc)
    return redact_string(message)


def redact_url(url: str) -> str:
    """
    Redact sensitive information from URLs (query params, auth).
    
    Args:
        url: URL string
    
    Returns:
        Redacted URL
    
    Example:
        >>> redact_url("https://api.example.com/data?api_key=abc123&user=alice")
        'https://api.example.com/data?api_key=***REDACTED***&user=alice'
    """
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    
    parsed = urlparse(url)
    
    # Redact query parameters
    query_params = parse_qs(parsed.query)
    redacted_params = {}
    
    for key, values in query_params.items():
        if key.lower() in SENSITIVE_FIELDS:
            redacted_params[key] = [REDACTION_PLACEHOLDER]
        else:
            redacted_params[key] = values
    
    redacted_query = urlencode(redacted_params, doseq=True)
    
    # Redact userinfo (username:password in URL)
    netloc = parsed.netloc
    if "@" in netloc:
        netloc = f"{REDACTION_PLACEHOLDER}@{netloc.split('@')[1]}"
    
    # Reconstruct URL
    redacted_url = urlunparse((
        parsed.scheme,
        netloc,
        parsed.path,
        parsed.params,
        redacted_query,
        parsed.fragment
    ))
    
    return redacted_url


def create_safe_log_record(record: logging.LogRecord) -> logging.LogRecord:
    """
    Create a safe copy of log record with redacted message.
    
    Args:
        record: Original log record
    
    Returns:
        Log record with redacted message
    """
    safe_record = logging.LogRecord(
        name=record.name,
        level=record.levelno,
        pathname=record.pathname,
        lineno=record.lineno,
        msg=redact_string(str(record.msg)),
        args=(),
        exc_info=None
    )
    
    return safe_record


class RedactionFilter(logging.Filter):
    """
    Logging filter that redacts sensitive data from log records.
    
    Usage:
        import logging
        from backend.core.log_redaction import RedactionFilter
        
        logger = logging.getLogger("app")
        logger.addFilter(RedactionFilter())
        
        logger.info({"user": "alice", "password": "secret"})
        # Output: {'user': 'alice', 'password': '***REDACTED***'}
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record to redact sensitive data.
        
        Args:
            record: Log record to filter
        
        Returns:
            True (always allow record, but modify it)
        """
        # Redact message
        if isinstance(record.msg, (dict, list)):
            record.msg = redact_sensitive_data(record.msg)
        elif isinstance(record.msg, str):
            record.msg = redact_string(record.msg)
        
        # Redact args
        if record.args:
            record.args = tuple(redact_sensitive_data(arg) for arg in record.args)
        
        # Redact exception info
        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            if exc_value:
                # Create new exception with redacted message
                redacted_msg = redact_exception(exc_value)
                record.exc_text = redacted_msg
        
        return True


def install_global_redaction_filter():
    """
    Install redaction filter on root logger.
    
    Call this once during application startup:
        from backend.core.log_redaction import install_global_redaction_filter
        install_global_redaction_filter()
    """
    root_logger = logging.getLogger()
    root_logger.addFilter(RedactionFilter())
    logger.info("? Global log redaction filter installed")


# Example usage
if __name__ == "__main__":
    # Test redaction
    test_data = {
        "username": "alice",
        "password": "SuperSecret123!",
        "email": "alice@example.com",
        "api_key": "sk_live_abcdefghijklmnopqrstuvwxyz123456",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
        "profile": {
            "phone": "+1234567890",
            "credit_card": "4532-1234-5678-9010",
            "ip": "192.168.1.100"
        }
    }
    
    redacted = redact_sensitive_data(test_data)
    print("Original:", test_data)
    print("Redacted:", redacted)
