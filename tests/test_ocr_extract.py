"""Tests for cautious OCR text parsing. No real-image accuracy claim."""
import unittest
from ocr_extract import parse_text

class OCRParserTests(unittest.TestCase):
    def test_english_sample(self):
        sample="""SYNTHETIC DEMO
        AIR CONDITIONER - SPLIT
        BRAND NASEEM
        MODEL AC-18000-X
        ANNUAL CONSUMPTION: 2400 kWh
        ENERGY EFFICIENCY: 12.5
        ENERGY LEVEL: B
        """
        result=parse_text(sample)
        self.assertEqual(result["model"],"AC-18000-X")
        self.assertEqual(result["brand"],"نسيم")
        self.assertEqual(result["device_type"],"مكيف")
        self.assertEqual(result["product_type"],"سبليت")
        self.assertEqual(result["annual_consumption"],"2400")
        self.assertEqual(result["energy_efficiency"],"12.5")
        self.assertEqual(result["efficiency_level"],"B")

    def test_missing_fields_do_not_get_invented(self):
        result=parse_text("MODEL AC-18000-X")
        self.assertEqual(result,{"model":"AC-18000-X"})

    def test_arabic_sample(self):
        result=parse_text("مكيف سبليت نسيم\nرقم الطراز AC-18000-X\nالاستهلاك السنوي ٢٤٠٠ ك.و.س")
        self.assertEqual(result.get("annual_consumption"),"2400")
        self.assertEqual(result.get("model"),"AC-18000-X")

    def test_empty_input(self):
        self.assertEqual(parse_text(""),{})

if __name__ == "__main__":
    unittest.main()
