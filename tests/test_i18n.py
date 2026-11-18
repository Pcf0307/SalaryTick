import unittest
import ast
import tempfile
import json
from pathlib import Path

from salary_tick.i18n import I18n, LANGUAGE_LABELS, normalize_language
from salary_tick.settings_store import SettingsStore


class I18nTests(unittest.TestCase):
    def test_unknown_language_falls_back_to_chinese(self):
        self.assertEqual(normalize_language("fr_FR"), "zh_CN")

    def test_chinese_returns_original_text(self):
        self.assertEqual(I18n("zh_CN").t("设置"), "设置")

    def test_english_translates_common_label(self):
        self.assertEqual(I18n("en_US").t("设置"), "Settings")

    def test_english_uses_segoe_ui(self):
        self.assertEqual(I18n("en_US").font_name, "Segoe UI")

    def test_chinese_uses_yahei(self):
        self.assertEqual(I18n("zh_CN").font_name, "Microsoft YaHei UI")

    def test_dynamic_overtime_status_is_translated(self):
        self.assertEqual(
            I18n("en_US").status("加班中，预计19:15结束"),
            "Overtime; expected end 19:15",
        )

    def test_record_source_is_translated(self):
        self.assertEqual(I18n("en_US").record_source("manual_override"), "Adjusted")

    def test_configure_styles_accepts_language_font(self):
        source_path = Path(__file__).parents[1] / "salary_tick" / "ui_styles.py"
        module = ast.parse(source_path.read_text(encoding="utf-8"))
        function = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "configure_styles")
        argument_names = [argument.arg for argument in function.args.args]
        self.assertEqual(argument_names, ["widget", "font_name"])
        self.assertEqual(ast.literal_eval(function.args.defaults[-1]), "Microsoft YaHei UI")

    def test_existing_config_without_language_gets_chinese_default(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text(json.dumps({"config_version": 2, "profile": {}}), encoding="utf-8")
            loaded = SettingsStore(path).load()
            self.assertEqual(loaded["display"]["language"], "zh_CN")

    def test_language_labels_are_stable(self):
        self.assertEqual(LANGUAGE_LABELS, {"zh_CN": "简体中文", "en_US": "English"})


if __name__ == "__main__":
    unittest.main()
