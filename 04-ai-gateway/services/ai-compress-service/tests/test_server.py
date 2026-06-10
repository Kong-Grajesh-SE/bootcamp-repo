import unittest
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../ai_compress_service")))

from ai_compress_service.server import app, init_globals, LLMLINGUA_MODEL_NAME_DEFAULT, LLMLINGUA_DEVICE_MAP_DEFAULT, count_tokens, path_prefix

class LLMCompressServiceTests(unittest.TestCase):
    def setUp(self):
        init_globals(LLMLINGUA_MODEL_NAME_DEFAULT, LLMLINGUA_DEVICE_MAP_DEFAULT)
        self.client = app.test_client()

    def test_compress_prompt_rate(self):
        payload = {
            "text": [{"msg_id": 1, "text": "Text that will be compressed without any llmlingua tags. And and I test using a stripped words like please"}],
            "compressor_type": "rate",
            "compression_ranges": [{ "min_tokens": 0, "max_tokens": 100, "value": 0.8 }],
            "model_name": "gpt-4",
            "advanced_logging": True,
        }
        response = self.client.post(path_prefix + "/compressPrompt", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        result = data["text"][0]["compressor_results"]
        self.assertEqual(data["text"][0]["msg_id"], 1)
        self.assertEqual(result["original_text"], payload["text"][0]["text"])
        self.assertIn("compress_prompt", data["text"][0])
        self.assertLess(count_tokens(data["text"][0]["compress_prompt"], "gpt-4"),
                        count_tokens(result["original_text"], "gpt-4"))

    def test_compress_prompt_rate_tags(self):
        payload = {
            "text": [{"msg_id": 1, "text": "Text is unthouched in this part. <LLMLINGUA>that will be compressed</LLMLINGUA>. Text is unthouched in this second part."}],
            "compressor_type": "rate",
            "compression_ranges": [{ "min_tokens": 0, "max_tokens": 100, "value": 0.8 }],
            "model_name": "gpt-4",
            "advanced_logging": True,
        }
        response = self.client.post(path_prefix + "/compressPrompt", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        result = data["text"][0]["compressor_results"]
        self.assertEqual(data["text"][0]["msg_id"], 1)
        self.assertIn("compress_prompt", data["text"][0])
        
        compress_prompt = data["text"][0]["compress_prompt"]
        part_1 = "Text is unthouched in this part"
        part_2 = "Text is unthouched in this second part"
        self.assertIn(part_1, compress_prompt)
        self.assertIn(part_2, compress_prompt)
    
        self.assertLess(count_tokens(result["compress_text"], "gpt-4"),
                        count_tokens(result["original_text"], "gpt-4"))

    def test_compress_prompt_target_token(self):
        payload = {
            "text": [{"msg_id": 2, "text": "Another very long part that should be compressed quite heavily. We need to make sure this part is longer than 15 tokens"}],
            "compressor_type": "target_token",
            "compression_ranges": [{ "min_tokens": 0, "max_tokens": 100, "value": 10 }],
            "model_name": "gpt-4",
            "advanced_logging": True,
        }
        response = self.client.post(path_prefix + "/compressPrompt", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        result = data["text"][0]["compressor_results"]
        self.assertEqual(data["text"][0]["msg_id"], 2)
        self.assertIn("compress_prompt", data["text"][0])
        compress_tokens = count_tokens(data["text"][0]["compress_prompt"], "gpt-4")
        self.assertLessEqual(compress_tokens, 15)

    def test_compress_prompt_target_tags(self):
        payload = {
            "text": [{"msg_id": 2, "text": "Text <LLMLINGUA>Another very long part that should be compressed quite heavily. We need to make sure this part is longer than 15 tokens</LLMLINGUA>."}],
            "compressor_type": "target_token",
            "compression_ranges": [{ "min_tokens": 0, "max_tokens": 100, "value": 10 }],
            "model_name": "gpt-4",
            "advanced_logging": True,
        }
        response = self.client.post(path_prefix + "/compressPrompt", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        result = data["text"][0]["compressor_results"]
        self.assertEqual(data["text"][0]["msg_id"], 2)
        self.assertIn("compress_prompt", data["text"][0])
        compress_tokens = count_tokens(result["compress_text"], "gpt-4")
        self.assertLessEqual(compress_tokens, 15)

    def test_invalid_compressor_type(self):
        payload = {
            "text": [{"msg_id": 3, "text": "Invalid compressor type"}],
            "compressor_type": "nonsense",
            "compression_ranges": [{ "min_tokens": 0, "max_tokens": 100, "value": 0.5 }],
            "model_name": "gpt-4"
        }
        response = self.client.post(path_prefix + "/compressPrompt", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())
        self.assertIn("compressor_type", response.get_json()["error"]["message"])

    def test_invalid_range_value_rate(self):
        payload = {
            "text": [{"msg_id": 4, "text": "Invalid rate value"}],
            "compressor_type": "rate",
            "compression_ranges": [{ "min_tokens": 0, "max_tokens": 100, "value": 1.5 }],
            "model_name": "gpt-4"
        }
        response = self.client.post(path_prefix + "/compressPrompt", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("must be > 0 and ≤ 1", response.get_json()["error"]["message"])

    def test_invalid_range_value_target_token(self):
        payload = {
            "text": [{"msg_id": 5, "text": "Invalid target token value"}],
            "compressor_type": "target_token",
            "compression_ranges": [{ "min_tokens": 0, "max_tokens": 100, "value": -10 }],
            "model_name": "gpt-4"
        }
        response = self.client.post(path_prefix + "/compressPrompt", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("must be a positive integer", response.get_json()["error"]["message"])

    def test_missing_model_name(self):
        payload = {
            "text": [{"msg_id": 6, "text": "Missing model name"}],
            "compressor_type": "rate",
            "compression_ranges": [{ "min_tokens": 0, "max_tokens": 100, "value": 0.5 }],
        }
        response = self.client.post(path_prefix + "/compressPrompt", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    def test_invalid_msg_id(self):
        payload = {
            "text": [{"msg_id": "abc", "text": "Bad msg_id"}],
            "compressor_type": "rate",
            "compression_ranges": [{ "min_tokens": 0, "max_tokens": 100, "value": 0.5 }],
            "model_name": "gpt-4"
        }
        response = self.client.post(path_prefix + "/compressPrompt", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("msg_id", response.get_json()["error"]["message"])

    def test_missing_compression_ranges(self):
        payload = {
            "text": [{"msg_id": 7, "text": "Missing compression_ranges"}],
            "compressor_type": "rate",
            "model_name": "gpt-4"
        }
        response = self.client.post(path_prefix + "/compressPrompt", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("compression_ranges", response.get_json()["error"]["message"])


if __name__ == "__main__":
    unittest.main()
