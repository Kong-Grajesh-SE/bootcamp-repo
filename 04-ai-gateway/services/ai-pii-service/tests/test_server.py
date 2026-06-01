import unittest
import sys
import os

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../ai_pii_service"))
)

from ai_pii_service.server import app

PASSWORD_REPLACEMENT = "########"
PASSWORD_ENTITY = "PASSWORD"

class PiiSanitizationTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def post_pii_request(self, data):
        return self.client.post("/llm/v1/sanitize", json=data)

    def post_credentials_request(self, data):
        return self.client.post("/llm/v1/sanitize_credentials", json=data)
    
    def do_asserts(self, status_code, res_json, num_results, redact_texts, entity_types):
        self.assertTrue(isinstance(num_results, int))
        self.assertTrue(num_results > -1)

        self.assertEqual(status_code, 200)
        self.assertEqual(num_results, len(res_json["text"][0]["analyzer_results"]))

        if isinstance(entity_types, str):
            self.assertTrue(isinstance(redact_texts, str))
            entity_types = [entity_types]
            redact_texts = [redact_texts]
        else:
            self.assertTrue(isinstance(redact_texts, list))
            self.assertTrue(isinstance(entity_types, list))
            self.assertEqual(num_results, len(entity_types))
            self.assertEqual(num_results, len(redact_texts))

        for i in range(num_results):
            self.assertEqual(entity_types[i], res_json["text"][0]["analyzer_results"][i]["entity_type"])
            self.assertIn(redact_texts[i], res_json["text"][0]["sanitized_text"])

    # Test with different anonymization types
    def test_different_anonymization_types(self):
        response = self.post_pii_request(
            {
                "text": "My phone number is 123-456-7890",
                "anonymize": ["phone"],
                "options": {"redact_type": "placeholder"},
            }
        )
        self.do_asserts(response.status_code, response.json, 1, "PLACEHOLDER1", "PHONE_NUMBER")

        response = self.post_pii_request(
            {
                "text": "My SSN is 206-98-6789",
                "anonymize": ["ssn"],
                "options": {"redact_type": "placeholder"},
            }
        )
        self.do_asserts(response.status_code, response.json, 1, "PLACEHOLDER1", "US_SSN")


        # flaky test, the passport can be identified as IN_PASSPORT or US_PASSPORT
        response = self.post_pii_request(
            {
                "text": "My passport is X12345678",
                "anonymize": ["passport"],
                "options": {"redact_type": "placeholder"},
            }
        )
        self.do_asserts(response.status_code, response.json, 1, "PLACEHOLDER1", "US_PASSPORT")

    # Anonymize only some categories
    def test_anonymize_some_categories(self):
        response = self.post_pii_request(
            {
                "text": "My name is John and I live in New York",
                "anonymize": ["general"],
                "options": {"redact_type": "placeholder"}
            }
        )
        self.do_asserts(response.status_code, response.json, 2, ["PLACEHOLDER1", "PLACEHOLDER2"], ["PERSON", "LOCATION"])

    def test_anonymize_url(self):
        response = self.post_pii_request(
            {
                "text": "The website of our company is https://www.konghq.com",
                "anonymize": ["url"],
                "options": {"redact_type": "placeholder"}
            }
        )
        self.do_asserts(response.status_code, response.json, 1, ["PLACEHOLDER1"], ["URL"])

    def test_anonymize_email(self):
        response = self.post_pii_request(
            {
                "text": "My name is John and my email is john0123@gmail.com",
                "anonymize": ["email"],
                "options": {"redact_type": "placeholder"}
            }
        )
        self.do_asserts(response.status_code, response.json, 1, ["PLACEHOLDER1"], ["EMAIL_ADDRESS"])

    def test_merged_entities(self):
        response = self.post_pii_request(
            {
                "text": "My name is Robin, I live in Shanghai China. My email is robin123@gmail.com",
                "anonymize": ["all"],
                "options": {"redact_type": "placeholder"}
            }
        )
        self.do_asserts(response.status_code, response.json, 3, ["PLACEHOLDER3", "PLACEHOLDER2", "PLACEHOLDER1"], ["PERSON", "LOCATION", "EMAIL_ADDRESS"])

    # 4) Anonymize all categories
    def test_anonymize_all_categories(self):
        response = self.post_pii_request(
            {
                "text": "My name is John, I live in New York and my phone is 123-456-7890.",
                "anonymize": ["all"],
                "options": {"redact_type": "placeholder"}
            }
        )
        self.do_asserts(response.status_code, response.json, 3, ["PLACEHOLDER3", "PLACEHOLDER2", "PLACEHOLDER1"], ["PERSON", "LOCATION", "PHONE_NUMBER"])

    # Test invalid category or category not identified
    def test_anonymize_invalid_category(self):
        response = self.post_pii_request(
            {
                "text": "My phone number is 123-456-7890",
                "anonymize": ["invalid_category"],
                "options": {"redact_type": "placeholder"}
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid item found in `anonymize`", response.json["error"])

    # Test for category that isn't in the text
    def test_anonymize_nonexistent_category(self):
        response = self.post_pii_request(
            {
                "text": "My name is John",
                "anonymize": ["ssn"],
                "options": {"redact_type": "placeholder"}
            }
        )
        self.do_asserts(response.status_code, response.json, 0, [], [])
        self.assertEqual(response.json["text"][0]["sanitized_text"], "My name is John")  # No SSN present in text
        self.assertEqual(
            response.json["identified_pii"], ["general"]
        )  # Only PERSON should be identified
        self.assertEqual(response.json["anonymized_pii"], [])  # No SSN present in text

    def test_sanitize_passwords(self):
        payload = {
            "text": "Hello world, this is John Doe and you can call me at 999-999-9999. "
            + "I live in Via San Bartolomeo 17. I really like to use kong products! "
            + "You can login with helloworld, try also S3mperPass and 'somepass123'. "
            + "Copyright, responsible. My password is 'sup3r$ecret'. "
            + "Here is another credential: iloveyou123. Another possible password: welcometomylife. "
            + "UnknownWordPassword and tok3napi. Otherwise try to login with username subnetmarco and password helloworld. "
            + "My pin is 12345 and 1234 and abcde. My lucky number is 9999."
        }
        response1 = self.post_credentials_request(payload)
        expected_num_credentials = 13
        self.do_asserts(response1.status_code, response1.json, expected_num_credentials,
            [ PASSWORD_REPLACEMENT for _ in range(expected_num_credentials) ],
            [ PASSWORD_ENTITY for _ in range(expected_num_credentials) ])

        self.assertEqual(response1.json["text"][0]["sanitized_text"],
            "Hello world, this is John Doe and you can call me at 999-999-9999. "
            + "I live in Via San Bartolomeo 17. I really like to use kong products! "
            + "You can login with ########, try also ######## and '########'. "
            + "Copyright, responsible. My password is '########'. "
            + "Here is another credential: ########. Another possible password: ########. "
            + "######## and ########. Otherwise try to login with username ######## and password ########. "
            + "My pin is ######## and ######## and ########. My lucky number is 9999.")

        payload.update({
            "anonymize": ["credentials"],
            "options": {"redact_type": "synthetic"}
        })
        response2 = self.post_pii_request(payload)
        self.do_asserts(response2.status_code, response2.json, expected_num_credentials,
            [ PASSWORD_REPLACEMENT for _ in range(expected_num_credentials) ],
            [ PASSWORD_ENTITY for _ in range(expected_num_credentials) ])

        self.assertEqual(response2.json["anonymized_pii"], response1.json["anonymized_pii"])
        self.assertEqual(response2.json["text"], response1.json["text"])

    def test_sanitize_empty_passwords(self):
        response = self.post_credentials_request({"text": "   "})
        self.do_asserts(response.status_code, response.json, 0, [], [])
        self.assertEqual(response.json["text"][0]["sanitized_text"], "   ")

    def test_sanitize_no_passwords(self):
        response = self.post_credentials_request(
            {"text": "Hello world, this thing has no passwords!"}
        )
        self.do_asserts(response.status_code, response.json, 0, [], [])
        self.assertEqual(response.json["text"][0]["sanitized_text"], "Hello world, this thing has no passwords!")

    def test_sanitize_passwords_different_language(self):
        response = self.post_credentials_request(
            {
                "text": "Per accedere il database PostgreSQL puoi usare utente default con password test123"
            }
        )
        self.do_asserts(response.status_code, response.json, 1, "########", "PASSWORD")
        self.assertEqual(
            response.json["text"][0]["sanitized_text"],
            "Per accedere il database PostgreSQL puoi usare utente default con password ########"
        )

    def test_sanitize_passwords_sample1(self):
        response = self.post_credentials_request(
            {"text": "Please enter your 4-digit PIN: 1234 to complete the transaction."}
        )
        self.do_asserts(response.status_code, response.json, 1, "########", "PASSWORD")
        self.assertEqual("Please enter your 4-digit PIN: ######## to complete the transaction.", response.json["text"][0]["sanitized_text"])

    def test_sanitize_passwords_sample2(self):
        response = self.post_credentials_request(
            {
                "text": "Your verification code is 987654. Use this code to log into your account."
            }
        )
        self.do_asserts(response.status_code, response.json, 1, "########", "PASSWORD")
        self.assertEqual("Your verification code is ########. Use this code to log into your account.", response.json["text"][0]["sanitized_text"])

    def test_sanitize_passwords_sample3(self):
        response = self.post_credentials_request(
            {
                "text": "The password for your Wi-Fi network is SecurePass123! Please don't share it with anyone."
            }
        )
        self.do_asserts(response.status_code, response.json, 1, "########", "PASSWORD")
        self.assertEqual(
            response.json["text"][0]["sanitized_text"],
            "The password for your Wi-Fi network is ########! Please don't share it with anyone."
        )

    def test_sanitize_passwords_sample4(self):
        response = self.post_credentials_request(
            {"text": "To reset your account, enter the recovery key: R3C0v3ryKey2024."}
        )
        self.do_asserts(response.status_code, response.json, 1, "########", "PASSWORD")
        self.assertEqual(
            response.json["text"][0]["sanitized_text"],
            "To reset your account, enter the recovery key: ########."
        )

    def test_sanitize_passwords_sample5(self):
        response = self.post_credentials_request(
            {
                "text": "Your one-time authentication token is 543210. This token will expire in 10 minutes."
            }
        )
        self.do_asserts(response.status_code, response.json, 1, "########", "PASSWORD")
        self.assertEqual("Your one-time authentication token is ########. This token will expire in 10 minutes.", response.json["text"][0]["sanitized_text"])

    def test_sanitize_passwords_sample6(self):
        response = self.post_credentials_request(
            {
                "text": "Enter your access code: ACC3SS2024, and your identifier: 882738, to proceed."
            }
        )
        self.do_asserts(response.status_code, response.json, 2, ["########", "########"], ["PASSWORD", "PASSWORD"])
        self.assertEqual(
            response.json["text"][0]["sanitized_text"],
            "Enter your access code: ########, and your identifier: ########, to proceed."
        )

    def test_sanitize_passwords_sample7(self):
        response = self.post_credentials_request(
            {
                "text": "Please confirm the challenge response with the security passcode 748392."
            }
        )
        self.do_asserts(response.status_code, response.json, 1, "########", "PASSWORD")
        self.assertEqual("Please confirm the challenge response with the security passcode ########.", response.json["text"][0]["sanitized_text"])

    def test_sanitize_passwords_sample8(self):
        response = self.post_credentials_request(
            {
                "text": "The passcode to unlock your account is 6a7b8c. It is valid for 5 minutes."
            }
        )
        self.do_asserts(response.status_code, response.json, 1, "########", "PASSWORD")
        self.assertEqual(
            response.json["text"][0]["sanitized_text"],
            "The passcode to unlock your account is ########. It is valid for 5 minutes."
        )

    def test_sanitize_passwords_sample9(self):
        response = self.post_credentials_request(
            {"text": "Your secret code for the ID verification process is 778899."}
        )
        self.do_asserts(response.status_code, response.json, 1, "########", "PASSWORD")
        self.assertEqual("Your secret code for the ID verification process is ########.", response.json["text"][0]["sanitized_text"])

    def test_sanitize_passwords_sample10(self):
        response = self.post_credentials_request(
            {
                "text": "The system has generated a temporary password for you: TempP@ssw0rd2023. Please change it after logging in."
            }
        )
        self.assertEqual(
            response.json["text"][0]["sanitized_text"],
            "The system has generated a temporary password for you: ########. Please change it after logging in."
        )

    def test_all_and_credentials_and_custom_patterns(self):
        payload = {
            "text": "My name is John Davis. I'm working in Kong company, my phone number is 123-456-7890."
            + "I have a laptop, its serial number is SN-123456. Its color is #C0C0C0. You can login with 12345.",
            "anonymize": ["all_and_credentials"],
            "options": {"redact_type": "placeholder"},
            "custom_patterns": [
                {
                    "name": "serial_number",
                    "regex": "SN-\\d{6}",
                    "score": 0.9
                },
                {
                    "name": "color",
                    "regex": "#[0-9a-fA-F]{6}",
                    "score": 0.9
                }
            ]
        }
        response = self.post_pii_request(payload)
        self.assertEqual(response.status_code, 200)
        res = response.json
        self.assertTrue(res.get("text"))
        self.assertTrue(res.get("duration"))
        for i in ["general", "phone", "credentials", "custom"]:
            self.assertIn(i, res["anonymized_pii"])
            self.assertIn(i, res["identified_pii"])

        self.assertEqual(res["detected_languages"], ["en"])

        name, company, phone = None, None, None
        credential, custom1, custom2 = None, None, None
        analyzer_results = res["text"][0]["analyzer_results"]
        for result in analyzer_results:
            if result["entity_type"] == "PERSON":
                name = result["redact_text"]
            elif result["entity_type"] == "LOCATION":
                company = result["redact_text"]
            elif result["entity_type"] == "PHONE_NUMBER":
                phone = result["redact_text"]
            elif result["entity_type"] == "PASSWORD":
                credential = result["redact_text"]
            elif result["entity_type"] == "CUSTOM" and not custom1:
                custom1 = result["redact_text"]
            elif result["entity_type"] == "CUSTOM":
                custom2 = result["redact_text"]

        expected_text = (f"My name is {name}. I'm working in {company} company, my phone number is {phone}."
            + f"I have a laptop, its serial number is {custom1}. Its color is {custom2}. You can login with {credential}.")

        self.assertEqual(res["text"][0]["sanitized_text"],
            expected_text
        )

if __name__ == "__main__":
    unittest.main()
