import unittest
import requests
import json

class PiiSanitizationTests(unittest.TestCase):
    BASE_URL = "http://localhost:8080/llm/v1"  # Update to your app's URL and port

    def test_health_check(self):
        """Test the health check endpoint"""
        response = requests.get(f"{self.BASE_URL}/status")
        self.assertEqual(response.status_code, 200)
        res_json = response.json()
        self.assertEqual(res_json["status"], "ok")
        self.assertIsNotNone(res_json["supported_languages"])

    def test_request_validation(self):
        def do_assert(payload, err_code, err_msg):
            response = requests.post(f"{self.BASE_URL}/sanitize", json=payload)
            self.assertEqual(response.status_code, err_code)
            self.assertEqual(response.json(), {"error": err_msg})

        invalid_testcases = [
            # test invalid text
            ({}, 400, "No valid `text` found"),
            ({"text": 1}, 400, "No valid `text` found"),
            ( { "text": [{ "text": "test"}], "anonymize": ["phone"], "options": {"redact_type": "placeholder"}}, 400, "No valid `msg_id` found"),
            ( { "text": [{ "text": 1, "msg_id": 1}], "anonymize": ["phone"], "options": {"redact_type": "placeholder"}}, 400, "`text` in the message is not string"),

            # test invalid anonymize
            ({"text": "test"}, 400, "No valid `anonymize` found"),
            ({"text": "test", "anonymize": 1}, 400, "No valid `anonymize` found"),
            ({"text": "test", "anonymize": [1]}, 400, "Invalid type of item found in `anonymize`: 1"),
            ({"text": "test", "anonymize": ["invalid"]}, 400, "Invalid item found in `anonymize`: invalid"),

            # test invalid custom_patterns
            ({"text": "test", "anonymize": ["all"], "custom_patterns": 1}, 400, "Invalid type of `custom_patterns`"),
            ({"text": "test", "anonymize": ["all"], "custom_patterns": {}}, 400, "Invalid type of `custom_patterns`"),
            ({"text": "test", "anonymize": ["all"], "custom_patterns": [{}]}, 400, "Invalid item found in `custom_patterns`"),
            ({"text": "test", "anonymize": ["all"], "custom_patterns": [{"name": "test", "regex": "\\d", "score": 100}]}, 400, "Invalid item found in `custom_patterns`"),
            ({"text": "test", "anonymize": ["all"], "custom_patterns": [{"name": "test", "regex": "\\d", "score": -100}]}, 400, "Invalid item found in `custom_patterns`"),
            ({"text": "test", "anonymize": ["all"], "custom_patterns": [{"name": " ", "regex": "\\d", "score": 0.1}]}, 400, "Invalid item found in `custom_patterns`"),
            ({"text": "test", "anonymize": ["all"], "custom_patterns": [{"name": "test", "regex": " ", "score": 0.1}]}, 400, "Invalid item found in `custom_patterns`"),

            # test invalid options
            ({"text": "test", "anonymize": ["all"]}, 400, "No valid `options` found"),
            ({"text": "test", "anonymize": ["all"], "options": 1}, 400, "No valid `options` found"),
            ({"text": "test", "anonymize": ["all"], "options": {}}, 400, "No valid `redact_type` found"),
            ({"text": "test", "anonymize": ["all"], "options": {"redact_type": 1}}, 400, "No valid `redact_type` found"),
            ({"text": "test", "anonymize": ["all"], "options": {"redact_type": "invalid"}}, 400, "No valid `redact_type` found")
        ]

        for payload, err_code, err_msg in invalid_testcases:
            do_assert(payload, err_code, err_msg)

    def test_anonymizing(self):
        testcases = [
            {
                "text": "My phone number is 123-456-7890",
                "anonymize": ["phone"],
                "options": {"redact_type": "synthetic"}
            },
            {
                "text": [{ "text": "My phone number is 123-456-7890", "msg_id": 1}],
                "anonymize": ["phone"],
                "options": {"redact_type": "synthetic"}
            }
        ]
        for payload in testcases:
            response = requests.post(f"{self.BASE_URL}/sanitize", json=payload)
            self.assertEqual(response.status_code, 200)
            res = response.json()
            self.assertEqual(res,
                {
                    "text": res["text"],
                    "identified_pii": ["phone"],
                    "anonymized_pii": ["phone"],
                    "detected_languages": ["en"],
                    "duration": res["duration"]
                }
            )

            text = res["text"]
            self.assertTrue(isinstance(text, list))
            self.assertEqual(len(text), 1)
            self.assertEqual(text[0]["detected_language"], "en")
            self.assertEqual(len(text[0]["analyzer_results"]), 1)
            self.assertEqual(1, text[0]["msg_id"])
            self.assertTrue(text[0]["sanitized_text"].startswith("My phone number is "))
        
        testcases = [
            {
                "text": "",
                "anonymize": ["phone"],
                "options": {"redact_type": "synthetic"},
            },
            {
                "text": [{ "text": "", "msg_id": 1}],
                "anonymize": ["phone"],
                "options": {"redact_type": "synthetic"},
            }
        ]

        for payload in testcases:
            response = requests.post(f"{self.BASE_URL}/sanitize", json=payload)
            self.assertEqual(response.status_code, 200)
            res = response.json()
            print("response: ", json.dumps(res))
            self.assertEqual(response.json(), {
                "text": [{
                    "sanitized_text": "",
                    "analyzer_results": [],
                    "detected_language": None,
                    "msg_id": 1
                }],
                "identified_pii": [],
                "anonymized_pii": [],
                "detected_languages": [],
                "duration": res["duration"]
            })

    def test_anonymizing_with_placeholder(self):
        payload = {
            "text": "My phone number is 123-456-7890",
            "anonymize": ["phone"],
            "options": {"redact_type": "placeholder"},
        }
        response = requests.post(f"{self.BASE_URL}/sanitize", json=payload)
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertEqual(len(res["text"]), 1)
        res["text"][0]["sanitized_text"] = "My phone number is PLACEHOLDER1"

    def test_sanitize_passwords(self):
        payload = {"text": "Please enter your 4-digit PIN: 1234 to complete the transaction."}
        response = requests.post(f"{self.BASE_URL}/sanitize_credentials", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            "Please enter your 4-digit PIN: ######## to complete the transaction.",
            response.json()["text"][0]["sanitized_text"]
        )
