import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS_DIRECTORY = PROJECT_ROOT / 'translations'
DEFAULT_LANGUAGE = 'en'
SUPPORTED_LANGUAGES = {'en', 'fr'}


class I18n:
    def __init__(self, language=DEFAULT_LANGUAGE):
        self.language = self._normalize_language(language)
        self._fallback_translations = self._load_translations(DEFAULT_LANGUAGE)
        self._translations = self._fallback_translations if self.language == DEFAULT_LANGUAGE else self._load_translations(self.language)

    def _normalize_language(self, language):
        normalized = (language or DEFAULT_LANGUAGE).strip().lower().split('_', 1)[0].split('-', 1)[0]
        return normalized if normalized in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE

    def _load_translations(self, language):
        path = TRANSLATIONS_DIRECTORY / f'{language}.json'
        with path.open('r', encoding='utf-8') as file:
            return json.load(file)

    def t(self, key, default=None, **kwargs):
        value = self._translations.get(key)
        if value is None:
            value = self._fallback_translations.get(key, default if default is not None else key)
        if kwargs:
            try:
                return value.format(**kwargs)
            except Exception:
                return value
        return value
