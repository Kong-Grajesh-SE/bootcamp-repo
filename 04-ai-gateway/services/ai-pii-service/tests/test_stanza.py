import unittest
import pytest
import requests

class PiiSanitizationTests(unittest.TestCase):
    BASE_URL = "http://localhost:8080/llm/v1"  # Update to your app's URL and port

    def post_pii_request(self, data):
        return self.client.post("/llm/v1/sanitize", json=data)
    
    # Turkish
    @pytest.mark.turkish
    def test_tr_anonymizing(self):

        self.maxDiff = None
        testcases = [
            {
                "text": "Benim adım Ahmet Yılmaz, numaram 123-456-7890.",
                "anonymize": ["general"],
                "options": {"redact_type": "placeholder"}
            }
        ]

        for payload in testcases:
            response = requests.post(f"{self.BASE_URL}/sanitize", json=payload)
            self.assertEqual(response.status_code, 200)
            res = response.json()
            self.assertEqual(res,
                {
                    "text": res["text"],
                    "identified_pii": ["general", "phone"],
                    "anonymized_pii": ["general"],
                    "detected_languages": ["tr"],
                    "duration": res["duration"]
                }
            )

            text = res["text"]
            self.assertTrue(isinstance(text, list))
            self.assertEqual(len(text), 1)
            self.assertEqual(text[0]["detected_language"], "tr")
            self.assertEqual(len(text[0]["analyzer_results"]), 1)
            self.assertEqual(1, text[0]["msg_id"])
            self.assertTrue(text[0]["sanitized_text"].startswith("Benim adım PLACEHOLDER1"))

    # Thai
    @pytest.mark.thai
    def test_th_anonymizing_email(self):
        payload = {
            # My name is xxx, I live in Bangkok, please contact me with robin.xiang@konghq.com
            "text": "ผมชื่อสมชาย อาศัยอยู่ในกรุงเทพฯ กรุณาติดต่อผมทางอีเมล: robin.xiang@konghq.com",
            "anonymize": ["all_and_credentials"],
            "options": {"redact_type": "placeholder"}
        }

        response = requests.post(f"{self.BASE_URL}/sanitize", json=payload)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        print(res["text"][0]["sanitized_text"])
        self.assertEqual(res["text"][0]["sanitized_text"], "ผมชื่อPLACEHOLDER3 อาศัยอยู่ในPLACEHOLDER2 กรุณาติดต่อผมทางอีเมล: PLACEHOLDER1")
        self.assertEqual(res["identified_pii"], ["email", "general"])
        self.assertEqual(res["anonymized_pii"], ["email", "general"])
        self.assertEqual(res["detected_languages"], ["th"])

    # Korean
    @pytest.mark.korean
    def test_ko_anonymizing(self):
        testcases = [
            {
                # This is <Name>, and you can call me at 010-1234-5678.I really like to use kong products!
                "text": "이것은 김민수입니다. 저에게는 010-1234-5678로 연락하시면 됩니다. 저는 Kong 제품을 정말 좋아합니다!",
                "anonymize": ["general"],
                "options": {"redact_type": "placeholder"}
            }
        ]

        for payload in testcases:
            response = requests.post(f"{self.BASE_URL}/sanitize", json=payload)
            self.assertEqual(response.status_code, 200)
            res = response.json()
            self.assertEqual(res,
                {
                    "text": res["text"],
                    "identified_pii": ["general"],
                    "anonymized_pii": ["general"],
                    "detected_languages": ["ko"],
                    "duration": res["duration"]
                }
            )

            text = res["text"]
            self.assertTrue(isinstance(text, list))
            self.assertEqual(len(text), 1)
            self.assertEqual(text[0]["detected_language"], "ko")
            self.assertEqual(len(text[0]["analyzer_results"]), 2)
            self.assertEqual(1, text[0]["msg_id"])
            self.assertEqual(text[0]["sanitized_text"], "이것은 PLACEHOLDER2. 저에게는 010-1234-5678로 연락하시면 됩니다. 저는 PLACEHOLDER1 제품을 정말 좋아합니다!")
