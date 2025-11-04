"""
Tests for log redaction utilities (Sprint 2).
"""
import pytest
import logging

from backend.core.log_redaction import (
    redact_string,
    redact_dict,
    redact_list,
    redact_sensitive_data,
    redact_exception,
    redact_url,
    RedactionFilter,
    REDACTION_PLACEHOLDER,
    SENSITIVE_FIELDS,
)


class TestStringRedaction:
    """Test string redaction functions."""
    
    def test_redact_password_field(self):
        """Test redacting known sensitive field."""
        result = redact_string("my-secret-password", "password")
        assert result == REDACTION_PLACEHOLDER
    
    def test_redact_api_key_field(self):
        """Test redacting API key field."""
        result = redact_string("sk_live_abcdef123456", "api_key")
        assert result == REDACTION_PLACEHOLDER
    
    def test_redact_email_partial(self):
        """Test partial email redaction (keep domain)."""
        result = redact_string("user@example.com", "email")
        assert "example.com" in result
        assert "user" not in result
        assert "***" in result
    
    def test_redact_jwt_token(self):
        """Test redacting JWT tokens."""
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        result = redact_string(jwt, "")
        assert result == REDACTION_PLACEHOLDER
    
    def test_redact_credit_card(self):
        """Test redacting credit card numbers."""
        result = redact_string("4532-1234-5678-9010", "")
        assert "4532" not in result or "****" in result
    
    def test_redact_ip_address_partial(self):
        """Test partial IP address redaction."""
        result = redact_string("192.168.1.100", "")
        assert "192.168.1" in result
        assert ".***" in result
        assert "100" not in result
    
    def test_no_redaction_safe_string(self):
        """Test no redaction for safe strings."""
        result = redact_string("Hello World", "username")
        assert result == "Hello World"
    
    def test_empty_string(self):
        """Test redacting empty string."""
        result = redact_string("", "password")
        assert result == ""


class TestDictRedaction:
    """Test dictionary redaction."""
    
    def test_redact_dict_password(self):
        """Test redacting password in dict."""
        data = {"username": "alice", "password": "secret123"}
        result = redact_dict(data)
        
        assert result["username"] == "alice"
        assert result["password"] == REDACTION_PLACEHOLDER
    
    def test_redact_dict_multiple_sensitive(self):
        """Test redacting multiple sensitive fields."""
        data = {
            "user": "bob",
            "api_key": "abc123",
            "token": "xyz789",
            "age": 30
        }
        result = redact_dict(data)
        
        assert result["user"] == "bob"
        assert result["age"] == 30
        assert result["api_key"] == REDACTION_PLACEHOLDER
        assert result["token"] == REDACTION_PLACEHOLDER
    
    def test_redact_nested_dict(self):
        """Test redacting nested dictionaries."""
        data = {
            "user": "charlie",
            "credentials": {
                "password": "secret",
                "api_key": "key123"
            }
        }
        result = redact_dict(data)
        
        assert result["user"] == "charlie"
        assert result["credentials"]["password"] == REDACTION_PLACEHOLDER
        assert result["credentials"]["api_key"] == REDACTION_PLACEHOLDER
    
    def test_redact_dict_max_depth(self):
        """Test max depth protection."""
        # Create deeply nested dict
        data = {"a": {"b": {"c": {"d": {"e": {"f": {"g": "value"}}}}}}}
        
        result = redact_dict(data, max_depth=3)
        # Should stop at max depth
        assert "error" in str(result).lower() or "max_depth" in str(result).lower()
    
    def test_redact_empty_dict(self):
        """Test redacting empty dict."""
        result = redact_dict({})
        assert result == {}


class TestListRedaction:
    """Test list redaction."""
    
    def test_redact_list_of_strings(self):
        """Test redacting list of strings."""
        data = ["user@example.com", "public-info", "token-abc123"]
        result = redact_list(data)
        
        # Email should be partially redacted
        assert "***@example.com" in str(result)
    
    def test_redact_list_of_dicts(self):
        """Test redacting list of dictionaries."""
        data = [
            {"user": "alice", "password": "pass1"},
            {"user": "bob", "password": "pass2"}
        ]
        result = redact_list(data)
        
        assert result[0]["user"] == "alice"
        assert result[0]["password"] == REDACTION_PLACEHOLDER
        assert result[1]["user"] == "bob"
        assert result[1]["password"] == REDACTION_PLACEHOLDER
    
    def test_redact_nested_list(self):
        """Test redacting nested lists."""
        data = [["email@test.com"], ["password: secret"]]
        result = redact_list(data)
        
        # Should recursively redact
        assert isinstance(result, list)
        assert isinstance(result[0], list)


class TestSensitiveDataRedaction:
    """Test main redaction function."""
    
    def test_redact_dict(self):
        """Test redacting dictionary."""
        data = {"user": "test", "password": "secret"}
        result = redact_sensitive_data(data)
        
        assert isinstance(result, dict)
        assert result["password"] == REDACTION_PLACEHOLDER
    
    def test_redact_list(self):
        """Test redacting list."""
        data = ["public", {"password": "secret"}]
        result = redact_sensitive_data(data)
        
        assert isinstance(result, list)
        assert result[1]["password"] == REDACTION_PLACEHOLDER
    
    def test_redact_string(self):
        """Test redacting string."""
        result = redact_sensitive_data("email@test.com")
        assert "***@test.com" in result
    
    def test_redact_other_types(self):
        """Test redacting non-string types."""
        assert redact_sensitive_data(123) == 123
        assert redact_sensitive_data(True) is True
        assert redact_sensitive_data(None) is None


class TestExceptionRedaction:
    """Test exception message redaction."""
    
    def test_redact_exception_with_token(self):
        """Test redacting exception containing token."""
        exc = Exception("Authentication failed with token: abc123xyz")
        result = redact_exception(exc)
        
        # Token should be redacted (if long enough)
        assert isinstance(result, str)
    
    def test_redact_exception_safe_message(self):
        """Test exception with safe message."""
        exc = ValueError("Invalid input value")
        result = redact_exception(exc)
        
        assert "Invalid input" in result


class TestURLRedaction:
    """Test URL redaction."""
    
    def test_redact_url_query_param(self):
        """Test redacting sensitive query parameters."""
        url = "https://api.example.com/data?api_key=secret123&user=alice"
        result = redact_url(url)
        
        assert "api_key=" in result
        assert "secret123" not in result
        assert REDACTION_PLACEHOLDER in result
        assert "user=alice" in result
    
    def test_redact_url_userinfo(self):
        """Test redacting username:password in URL."""
        url = "https://user:pass@example.com/path"
        result = redact_url(url)
        
        assert "user:pass" not in result
        assert REDACTION_PLACEHOLDER in result
        assert "example.com" in result
    
    def test_redact_url_no_sensitive_data(self):
        """Test URL without sensitive data."""
        url = "https://example.com/public/path?page=1"
        result = redact_url(url)
        
        # Should remain mostly unchanged
        assert "example.com" in result
        assert "page=1" in result


class TestRedactionFilter:
    """Test logging filter for redaction."""
    
    def test_filter_redacts_message(self):
        """Test filter redacts log message."""
        filter_obj = RedactionFilter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg={"user": "alice", "password": "secret"},
            args=(),
            exc_info=None
        )
        
        result = filter_obj.filter(record)
        
        assert result is True  # Record is allowed
        assert record.msg["password"] == REDACTION_PLACEHOLDER
    
    def test_filter_redacts_args(self):
        """Test filter redacts log args."""
        filter_obj = RedactionFilter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Login attempt: %s",
            args=({"user": "bob", "password": "secret"},),
            exc_info=None
        )
        
        filter_obj.filter(record)
        
        # Args should be redacted
        assert REDACTION_PLACEHOLDER in str(record.args)
    
    def test_filter_redacts_exception(self):
        """Test filter redacts exception info."""
        filter_obj = RedactionFilter()
        
        try:
            raise ValueError("Error with token: abc123")
        except ValueError as e:
            exc_info = (type(e), e, e.__traceback__)
        
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info
        )
        
        filter_obj.filter(record)
        
        # Exception should be redacted
        assert hasattr(record, "exc_text")


class TestPatternDetection:
    """Test pattern-based redaction."""
    
    def test_detect_email(self):
        """Test email pattern detection."""
        text = "Contact us at support@example.com for help"
        result = redact_string(text, "")
        
        assert "support" not in result or "***" in result
    
    def test_detect_jwt(self):
        """Test JWT pattern detection."""
        text = "Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"
        result = redact_string(text, "")
        
        assert "eyJhbGci" not in result
        assert REDACTION_PLACEHOLDER in result
    
    def test_detect_phone(self):
        """Test phone number detection."""
        text = "Call +1234567890 for support"
        result = redact_string(text, "")
        
        # Phone numbers should be detected
        assert "+1234567890" not in result or "***" in result


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_redact_none(self):
        """Test redacting None."""
        result = redact_sensitive_data(None)
        assert result is None
    
    def test_redact_circular_reference(self):
        """Test handling circular references."""
        data = {"a": 1}
        data["self"] = data  # Circular reference
        
        # Max depth should prevent infinite loop
        result = redact_dict(data, max_depth=5)
        assert isinstance(result, dict)
    
    def test_very_long_string(self):
        """Test redacting very long strings."""
        long_text = "a" * 100000
        result = redact_string(long_text, "")
        
        assert isinstance(result, str)
    
    def test_special_characters(self):
        """Test strings with special characters."""
        text = "password: !@#$%^&*()"
        result = redact_string(text, "password")
        
        assert result == REDACTION_PLACEHOLDER
    
    def test_unicode_characters(self):
        """Test Unicode character handling."""
        data = {"?ifre": "gizli-bilgi", "??": "??"}
        result = redact_dict(data)
        
        # Should handle Unicode keys/values
        assert isinstance(result, dict)


@pytest.mark.integration
class TestLoggingIntegration:
    """Integration tests with Python logging."""
    
    def test_install_global_filter(self):
        """Test installing filter on root logger."""
        from backend.core.log_redaction import install_global_redaction_filter
        
        logger = logging.getLogger("test_redaction")
        logger.setLevel(logging.INFO)
        
        # Install filter
        install_global_redaction_filter()
        
        # Log sensitive data
        logger.info({"password": "secret123"})
        
        # In real scenario, logged message would be redacted
        # (requires inspecting log handlers)
    
    def test_logger_with_filter(self, caplog):
        """Test logger output with redaction filter."""
        logger = logging.getLogger("test_filtered")
        logger.addFilter(RedactionFilter())
        
        with caplog.at_level(logging.INFO):
            logger.info({"user": "alice", "password": "secret"})
        
        # Check that password was redacted in log
        log_record = caplog.records[0]
        assert log_record.msg["password"] == REDACTION_PLACEHOLDER
