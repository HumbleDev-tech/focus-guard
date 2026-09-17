"""
Tests for client.i18n internationalization engine.
Validates 100% key parity, locale resolution, and interpolation.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication

from client.i18n import (
    TRANSLATIONS,
    t,
    get_configured_language_setting,
    set_configured_language_setting,
    resolve_active_language,
    get_available_languages
)

_app = QApplication.instance() or QApplication(sys.argv)


class TestI18nEngine(unittest.TestCase):
    def setUp(self):
        # Save original language setting
        self.original_lang = get_configured_language_setting()

    def tearDown(self):
        # Restore original setting
        set_configured_language_setting(self.original_lang)

    def test_complete_key_parity(self):
        """Ensures that all keys in 'es' exist in 'en' and vice-versa."""
        es_keys = set(TRANSLATIONS["es"].keys())
        en_keys = set(TRANSLATIONS["en"].keys())

        missing_in_en = es_keys - en_keys
        missing_in_es = en_keys - es_keys

        self.assertEqual(
            missing_in_en,
            set(),
            f"Keys present in 'es' but missing in 'en': {missing_in_en}"
        )
        self.assertEqual(
            missing_in_es,
            set(),
            f"Keys present in 'en' but missing in 'es': {missing_in_es}"
        )

    def test_translation_switching(self):
        """Verifies that setting language to 'es' or 'en' changes returned text."""
        set_configured_language_setting("es")
        self.assertEqual(resolve_active_language(), "es")
        self.assertEqual(t("app.title"), "Focus-Guard")
        self.assertEqual(t("tab.domains"), "Sitios Bloqueados")
        self.assertEqual(t("app.btn_save"), "Guardar Reglas (Ctrl+S)")

        set_configured_language_setting("en")
        self.assertEqual(resolve_active_language(), "en")
        self.assertEqual(t("tab.domains"), "Blocked Sites")
        self.assertEqual(t("app.btn_save"), "Save Rules (Ctrl+S)")

    def test_parameter_interpolation(self):
        """Verifies named parameter formatting works in both languages."""
        set_configured_language_setting("es")
        formatted_es = t("domains.btn_remove_tooltip", domain="reddit.com")
        self.assertEqual(formatted_es, "Eliminar reddit.com")

        set_configured_language_setting("en")
        formatted_en = t("domains.btn_remove_tooltip", domain="reddit.com")
        self.assertEqual(formatted_en, "Remove reddit.com")

    def test_fallback_for_missing_key(self):
        """Non-existent key should return the key itself."""
        res = t("non.existent.key.xyz")
        self.assertEqual(res, "non.existent.key.xyz")

    def test_available_languages_structure(self):
        langs = get_available_languages()
        self.assertIn("auto", langs)
        self.assertIn("es", langs)
        self.assertIn("en", langs)


if __name__ == "__main__":
    unittest.main()
