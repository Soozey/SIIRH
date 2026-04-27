import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGET_FILES = [
    PROJECT_ROOT / "siirh-backend" / "app" / "routers" / "reporting.py",
    PROJECT_ROOT / "siirh-backend" / "app" / "routers" / "workers_import.py",
    PROJECT_ROOT / "siirh-backend" / "app" / "services" / "recruitment_assistant_service.py",
    PROJECT_ROOT / "siirh-frontend" / "src" / "pages" / "Reporting.tsx",
    PROJECT_ROOT / "siirh-frontend" / "src" / "pages" / "Organization.tsx",
]
FORBIDDEN_PATTERNS = ["Ã", "Â", "â€™", "â€œ", "â€", "�"]


class EncodingGuardrailTests(unittest.TestCase):
    def test_target_files_are_utf8_clean(self):
        for file_path in TARGET_FILES:
            content = file_path.read_text(encoding="utf-8")
            for pattern in FORBIDDEN_PATTERNS:
                self.assertNotIn(pattern, content, f"{pattern!r} found in {file_path}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
