import unittest
import requests
import json
import sys
import os

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../ai_compress_service"))
)

from ai_compress_service.server import count_tokens

method_prefix = "llm.v1."
path_prefix = "/llm/v1"

class CompressPromptTests(unittest.TestCase):
    SERVER_URL = "http://localhost:8080"
    BASE_URL = SERVER_URL + path_prefix

    def test_health_check(self):
        response = requests.get(f"{self.SERVER_URL}/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("status"), "ok")

    def test_invalid_inputs(self):
        testcases = [
            ({}, 400, "No valid `text` found"),
            ({"text": 123, "model_name": "gpt-4"}, 400, "No valid `text` found"),
            ({"text": [{"text": "sample"}], "model_name": "gpt-4", "compressor_type": "rate", "compression_ranges": [{ "min_tokens": 0, "max_tokens": 100, "value": 0.5 }]}, 400, "No valid `msg_id` found"),
            ({"text": [{"text": 1, "msg_id": 1}], "model_name": "gpt-4", "compressor_type": "rate", "compression_ranges": [{ "min_tokens": 0, "max_tokens": 100, "value": 0.5 }]}, 400, "`text` in the message is not string"),
            ({"text": "test"}, 400, "Error: You must provide 'model_name'."),
            ({"text": "test", "model_name": "gpt-4"}, 400, "Error: You must provide 'compressor_type'."),
            ({"text": "test", "model_name": "gpt-4", "compressor_type": "rate", "compression_ranges": [{ "min_tokens": 0, "max_tokens": 100, "value": 1.5 }]}, 400, "in range 1 must be > 0 and ≤ 1"),
        ]

        for payload, err_code, err_msg in testcases:
            response = requests.post(f"{self.BASE_URL}/compressPrompt", json=payload)
            self.assertEqual(response.status_code, err_code)
            self.assertIn(err_msg, response.text)

    def test_basic_compression_ratio(self):
        payload = {
            "text": [
                {
                    "msg_id": 1,
                    "text": "Hi this is a long text with redundant and important parts we want to compress down."
                },
                {
                    "msg_id": 2,
                    "text": "Another message that should be compressed as well."
                }
            ],
            "compressor_type": "rate",
            "compression_ranges": [
                { "min_tokens": 0, "max_tokens": 1000, "value": 0.8 }
            ],
            "model_name": "gpt-4",
            "advanced_logging": True,
        }

        response = requests.post(f"{self.BASE_URL}/compressPrompt", json=payload)
        self.assertEqual(response.status_code, 200)
        res = response.json()

        self.assertIn("text", res)
        self.assertTrue(isinstance(res["text"], list))
        for msg in res["text"]:
            result = msg["compressor_results"]
            self.assertIn("compress_type", result)
            self.assertEqual(result["compress_type"], "rate")
            self.assertIn("compress_value", result)
            self.assertLess(len(msg["compress_prompt"]), len(result["original_text"]))

    def test_jsonrpc_compression_target_token(self):
        rpc_payload = {
            "jsonrpc": "2.0",
            "method": "llm.v1.compressPrompt",
            "id": 101,
            "params": {
                "text": [
                    {
                        "msg_id": 9,
                        "text": "This part is short so no compress."
                    },
                    {
                        "msg_id": 10,
                        "text": "This is a longer text message that should be compressed based on target token count. Make sure it is longer than 20 tokens so I am adding a few words like this."
                    },
                    {
                        "msg_id": 11,
                        "text": (
                            "Here is an example message for compression testing. This Part will be untouched."
                            "<LLMLINGUA>Only this part should be compressed as it is surrounded by the llmlingua tags.</LLMLINGUA>"
                            "Another example message for compression testing. This Part will be untouched."
                        )
                    },
                ],
                "compressor_type": "target_token",
                "compression_ranges": [
                    { "min_tokens": 0, "max_tokens": 20, "value": 10 },
                    { "min_tokens": 20, "max_tokens": 50, "value": 15 }
                ],
                "model_name": "gpt-4",
                "advanced_logging": True,
            }
        }

        response = requests.post(f"{self.SERVER_URL}/", json=rpc_payload)
        self.assertEqual(response.status_code, 200)
        res = response.json()

        compress_results = res["result"]["text"]
        for msg in compress_results:
            result = msg["compressor_results"]
            original_token_count = count_tokens(result["original_text"], "gpt-4")
            if msg["msg_id"] == 9:
                self.assertNotIn("compress_text", result)
                self.assertEqual(result["save_token_count"], 0)
            else:
                compressed_token_count = count_tokens(result["compress_text"], "gpt-4")
                save_token_count = original_token_count - compressed_token_count
                self.assertEqual(result["compress_type"], "target_token")
                self.assertLess(compressed_token_count, original_token_count)

            if msg["msg_id"] == 10:
                self.assertIn("compress_text", result)
                self.assertEqual(result["compress_value"], 15)

            if msg["msg_id"] == 11:
                self.assertIn("compress_text", result)
                self.assertEqual(result["compress_value"], 10)
                prefix = "Here is an example message for compression testing. This Part will be untouched."
                suffix = "Another example message for compression testing. This Part will be untouched."
                self.assertTrue(msg["compress_prompt"].startswith(prefix))
                self.assertTrue(msg["compress_prompt"].endswith(suffix))
                self.assertNotIn(
                    "Only this part should be compressed as it is surrounded by the llmlingua tags.",
                    msg["compress_prompt"]
                )

if __name__ == "__main__":
    unittest.main()
