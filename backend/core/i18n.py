"""
Backend i18n (Internationalization) Helper
Default Language: Turkish (tr)
Phase 16-TR Mode

Usage:
    from backend.core.i18n import tr_message, tr_error, tr_success
    
    return {"message": tr_success("seller_added_blocklist")}
"""

from typing import Dict, Optional

# Turkish translations for backend responses
TR_MESSAGES: Dict[str, str] = {
    # Success messages
    "seller_added_allowlist": "Sat?c? izin listesine eklendi",
    "seller_added_blocklist": "Sat?c? engel listesine eklendi",
    "seller_removed_allowlist": "Sat?c? izin listesinden kald?r?ld?",
    "seller_removed_blocklist": "Sat?c? engel listesinden kald?r?ld?",
    "preferences_updated": "Tercihler g?ncellendi",
    "operation_successful": "??lem ba?ar?l?",
    "created_successfully": "Ba?ar?yla olu?turuldu",
    "updated_successfully": "Ba?ar?yla g?ncellendi",
    "deleted_successfully": "Ba?ar?yla silindi",
    
    # Error messages
    "unauthorized": "Yetkisiz eri?im",
    "forbidden": "Bu i?lem i?in yetkiniz yok",
    "not_found": "Kaynak bulunamad?",
    "validation_error": "Ge?ersiz veri giri?i",
    "server_error": "Sunucu hatas? olu?tu",
    "database_error": "Veritaban? hatas?",
    "network_error": "A? ba?lant? hatas?",
    "timeout": "?stek zaman a??m?na u?rad?",
    "duplicate_entry": "Bu kay?t zaten mevcut",
    "invalid_credentials": "Ge?ersiz kimlik bilgileri",
    "session_expired": "Oturum s?resi doldu",
    "rate_limit_exceeded": "?ok fazla istek g?nderdiniz, l?tfen bekleyin",
    "invalid_action": "Ge?ersiz i?lem",
    "seller_not_found": "Sat?c? bulunamad?",
    "already_in_list": "Sat?c? zaten listede mevcut",
    "not_in_list": "Sat?c? listede bulunamad?",
    
    # Validation errors
    "required_field": "Bu alan zorunludur",
    "invalid_email": "Ge?ersiz e-posta adresi",
    "invalid_format": "Ge?ersiz format",
    "min_length": "Minimum {min} karakter olmal?d?r",
    "max_length": "Maksimum {max} karakter olmal?d?r",
    "invalid_seller_id": "Ge?ersiz sat?c? kimli?i",
    "invalid_source": "Ge?ersiz kaynak",
    
    # Seller preference specific
    "blocked_by_user_preference": "Kullan?c? tercihi taraf?ndan engellendi",
    "seller_not_allowed": "Bu sat?c?ya teklif verilmesine izin verilmiyor",
    "allowlist_restricted": "?zin listesi k?s?tl? modda",
    "seller_in_blocklist": "Sat?c? engel listesinde",
    
    # AutoBid messages
    "autobid_started": "Otomatik teklif ba?lat?ld?",
    "autobid_stopped": "Otomatik teklif durduruldu",
    "bid_placed": "Teklif verildi",
    "bid_failed": "Teklif verilemedi",
    "budget_exceeded": "B?t?e a??ld?",
    "confidence_too_low": "G?ven skoru ?ok d???k",
    
    # Auction messages
    "auction_not_found": "M?zayede bulunamad?",
    "auction_ended": "M?zayede sona erdi",
    "auction_not_started": "M?zayede hen?z ba?lamad?",
    
    # General
    "loading": "Y?kleniyor",
    "processing": "??leniyor",
    "completed": "Tamamland?",
    "failed": "Ba?ar?s?z",
    "cancelled": "?ptal edildi",
}


def tr_message(key: str, **kwargs) -> str:
    """
    Get Turkish translation for a message key
    
    Args:
        key: Translation key
        **kwargs: Variables for string interpolation
    
    Returns:
        Translated message string
        
    Example:
        tr_message("seller_added_blocklist")
        # Returns: "Sat?c? engel listesine eklendi"
        
        tr_message("min_length", min=5)
        # Returns: "Minimum 5 karakter olmal?d?r"
    """
    message = TR_MESSAGES.get(key, key)
    
    # Interpolate variables if provided
    if kwargs:
        try:
            message = message.format(**kwargs)
        except KeyError:
            pass  # Return message without interpolation if key doesn't exist
    
    return message


def tr_success(key: str, **kwargs) -> str:
    """
    Get Turkish translation for success message
    
    Args:
        key: Translation key
        **kwargs: Variables for string interpolation
        
    Returns:
        Translated success message
    """
    return tr_message(key, **kwargs)


def tr_error(key: str, **kwargs) -> str:
    """
    Get Turkish translation for error message
    
    Args:
        key: Translation key
        **kwargs: Variables for string interpolation
        
    Returns:
        Translated error message
    """
    return tr_message(key, **kwargs)


def tr_validation(key: str, **kwargs) -> str:
    """
    Get Turkish translation for validation error
    
    Args:
        key: Translation key
        **kwargs: Variables for string interpolation
        
    Returns:
        Translated validation error message
    """
    return tr_message(key, **kwargs)


def get_locale() -> str:
    """
    Get current locale
    
    Returns:
        Current locale code (always 'tr' for Phase 16-TR)
    """
    return "tr"


def format_datetime_tr(dt) -> str:
    """
    Format datetime in Turkish locale (DD.MM.YYYY HH:mm)
    
    Args:
        dt: datetime object
        
    Returns:
        Formatted datetime string
    """
    return dt.strftime("%d.%m.%Y %H:%M")


def format_date_tr(dt) -> str:
    """
    Format date in Turkish locale (DD.MM.YYYY)
    
    Args:
        dt: date or datetime object
        
    Returns:
        Formatted date string
    """
    return dt.strftime("%d.%m.%Y")


class TurkishResponse:
    """
    Helper class for creating Turkish-localized API responses
    """
    
    @staticmethod
    def success(message_key: str, data: Optional[Dict] = None, **kwargs) -> Dict:
        """
        Create success response with Turkish message
        
        Args:
            message_key: Translation key
            data: Optional response data
            **kwargs: Variables for message interpolation
            
        Returns:
            Response dict with Turkish message
        """
        response = {
            "success": True,
            "message": tr_success(message_key, **kwargs)
        }
        if data:
            response["data"] = data
        return response
    
    @staticmethod
    def error(message_key: str, status_code: int = 400, **kwargs) -> Dict:
        """
        Create error response with Turkish message
        
        Args:
            message_key: Translation key
            status_code: HTTP status code
            **kwargs: Variables for message interpolation
            
        Returns:
            Response dict with Turkish error message
        """
        return {
            "success": False,
            "error": tr_error(message_key, **kwargs),
            "status_code": status_code
        }


# Convenience instances
tr_response = TurkishResponse()
