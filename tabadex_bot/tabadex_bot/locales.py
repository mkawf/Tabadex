# tabadex_bot/locales.py

import json
from pathlib import Path

# Path to the locales directory
LOCALE_DIR = Path(__file__).parent.parent / 'locales'

# Load all available translations
translations = {}
for file in LOCALE_DIR.glob('*.json'):
    lang_code = file.stem
    with open(file, 'r', encoding='utf-8') as f:
        translations[lang_code] = json.load(f)

DEFAULT_LANG = 'fa'

def get_text(key: str, lang_code: str = DEFAULT_LANG) -> str:
    """
    Fetches a translated text string for a given key and language.
    Falls back to the default language if the key is not found in the specified language.
    """
    lang_code = lang_code if lang_code in translations else DEFAULT_LANG
    
    # Try to get from the selected language
    text = translations.get(lang_code, {}).get(key)
    if text:
        return text

    # Fallback to default language
    text = translations.get(DEFAULT_LANG, {}).get(key)
    if text:
        return text

    # If key is not found anywhere, return the key itself
    return key