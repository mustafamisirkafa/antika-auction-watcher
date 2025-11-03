"""
Configuration updates for Phase 16-TR Mode
Add these settings to backend/config.py or .env
"""

# Default language setting
DEFAULT_LANGUAGE = "tr"
DEFAULT_LOCALE = "tr_TR"

# Date/time formatting
DATE_FORMAT = "%d.%m.%Y"  # DD.MM.YYYY
DATETIME_FORMAT = "%d.%m.%Y %H:%M"  # DD.MM.YYYY HH:mm
TIME_FORMAT = "%H:%M"

# Currency formatting
CURRENCY_CODE = "TRY"
CURRENCY_SYMBOL = "?"

# i18n settings
I18N_ENABLED = True
I18N_FALLBACK_ENABLED = True
I18N_DEFAULT_LANG = "tr"

# Add to Settings class in config.py:
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Phase 16-TR: Localization settings
    default_language: str = "tr"
    default_locale: str = "tr_TR"
    date_format: str = "%d.%m.%Y"
    datetime_format: str = "%d.%m.%Y %H:%M"
    currency_code: str = "TRY"
    
    class Config:
        env_file = ".env"
