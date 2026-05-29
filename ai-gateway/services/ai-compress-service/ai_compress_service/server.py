import os
import time
import argparse
import logging
import json
import re
from flask import Flask, request, jsonify
from flask.json.provider import DefaultJSONProvider
from llmlingua import PromptCompressor
import tiktoken
import torch
import platform
import sys

llmlingua_model_name_global = None
llmlingua_device_map_global = None

method_prefix = "llm.v1."
path_prefix = "/llm/v1"

LLMLINGUA_MODEL_NAME_LIST = [
    "microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
    "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"
]

LLMLINGUA_DEVICE_MAP_LIST = [ "cuda", "cpu", "mps", "balanced", "balanced_low_0", "auto" ]

LLMLINGUA_MODEL_NAME_DEFAULT = "microsoft/llmlingua-2-xlm-roberta-large-meetingbank"
LLMLINGUA_DEVICE_MAP_DEFAULT = "cpu"

class CustomJSONProvider(DefaultJSONProvider):
    def dumps(self, obj, **kwargs):
        kwargs.setdefault('ensure_ascii', False)
        return json.dumps(obj, **kwargs)

    def loads(self, s, **kwargs):
        return json.loads(s, **kwargs)

LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

app = Flask(__name__)
app.json_provider_class = CustomJSONProvider
app.json = app.json_provider_class(app)

compressor = None  # Global instance

def current_milli_time():
    return round(time.time() * 1000)

def validate_rpc_request(data):
    if not data:
        return False, "Invalid request: no request body"
    if data.get("jsonrpc") != "2.0":
        return False, "Invalid request: jsonrpc must be '2.0'"
    if "method" not in data or "params" not in data or "id" not in data:
        return False, "Invalid request: missing fields"
    return True, None

def jsonrpc_response(result, id):
    return jsonify({"jsonrpc": "2.0", "result": result, "id": id})

def jsonrpc_error_response(message, id):
    return jsonify({"jsonrpc": "2.0", "error": {"message": message}, "id": id})

def load_model(llmlingua_model_name, llmlingua_device_map):

    return PromptCompressor(
        model_name=llmlingua_model_name,
        use_llmlingua2=True,
        device_map=llmlingua_device_map, # Options include 'cuda', 'cpu', 'mps', 'balanced', 'balanced_low_0', 'auto'
    )

def init_globals(llmlingua_model_name, llmlingua_device_map):
    global compressor, llmlingua_model_name_global, llmlingua_device_map_global

    if not llmlingua_device_map:
        raise EnvironmentError("Device map not set in environment")

    if llmlingua_device_map not in LLMLINGUA_DEVICE_MAP_LIST:
        raise EnvironmentError(f"Device map {llmlingua_device_map} is not supported. Allowed: {LLMLINGUA_DEVICE_MAP_LIST}")

    if llmlingua_device_map in ("cuda", "balanced", "balanced_low_0", "auto") and not torch.cuda.is_available():
        raise EnvironmentError(f"Device map '{llmlingua_device_map}' is not supported on this platform because CUDA is unavailable.")

    if llmlingua_device_map == "mps" and platform.system() != "Darwin":
        raise EnvironmentError(f"Device map {llmlingua_device_map} is not supported on this platform.")

    if not llmlingua_model_name:
        raise EnvironmentError("LLMLINGUA_MODEL_NAME not set in environment")

    # allow either a model (auto download from HF), or a local downloaded model
    if llmlingua_model_name not in LLMLINGUA_MODEL_NAME_LIST and not llmlingua_model_name.startswith("/"):
        raise EnvironmentError(f"Model {llmlingua_model_name} is not supported. Allowed: {LLMLINGUA_MODEL_NAME_LIST}")

    compressor = load_model(llmlingua_model_name, llmlingua_device_map)
    llmlingua_model_name_global = llmlingua_model_name    
    llmlingua_device_map_global = llmlingua_device_map

def strip_politeness(text: str) -> str:
    polite_phrases = [
        r"\bhello\b", r"\bhi\b", r"\bhey\b",
        r"\bplease\b", r"\bcould you\b", r"\bcan you\b",
        r"\bwould you\b", r"\bkindly\b", r"\bthank you\b", r"\bthanks\b",
        r"\ba lot\b", r"\bregards\b", r"\bsincerely\b"
    ]
    pattern = re.compile("|".join(polite_phrases), re.IGNORECASE)
    return re.sub(r"\s+", " ", pattern.sub("", text)).strip()

def count_tokens(text, model_name):
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        print(f"[Fallback] Model '{model_name}' not supported, falling back to 'cl100k_base' encoding.")
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            return f"Error using fallback encoding: {str(e)}"
    try:
        num_tokens = len(encoding.encode(text))
        return num_tokens
    except Exception as e:
        return f"Encoding error: {str(e)}"

def compress_text_f(text, compressor_type, compressor_value):
    compress_args = {
        "force_tokens": ["!", ".", "?", "\n"],
        "drop_consecutive": True,
        "force_reserve_digit": True,
    }

    compress_args[compressor_type] = compressor_value

    return compressor.compress_prompt(text, **compress_args)

# not implemented yet in llm-lingua-2
def structured_compress_prompt(text):
    return compressor.structured_compress_prompt(text)

def validate_compression_ranges(compression_ranges, compressor_type):
    if compression_ranges is None:
        raise ValueError("Error: You must provide 'compression_ranges'.")
    if not isinstance(compression_ranges, list):
        raise ValueError("Error: 'compression_ranges' must be a list.")
    if len(compression_ranges) == 0:
        raise ValueError("Error: 'compression_ranges' list cannot be empty.")
    
    for i, cr in enumerate(compression_ranges):
        if not isinstance(cr, dict):
            raise ValueError(f"Error: Range {i+1} in 'compression_ranges' must be a dict.")
        for key in ("min_tokens", "max_tokens", "value"):
            if key not in cr:
                raise ValueError(f"Error: Range {i+1} missing required key '{key}'.")

        if not isinstance(cr["min_tokens"], int) or not isinstance(cr["max_tokens"], int):
            raise ValueError(f"Error: 'min_tokens' and 'max_tokens' must be integers in range {i+1}.")

        if not isinstance(cr["value"], (int, float)):
            raise ValueError(f"Error: 'value' must be a number in range {i+1}.")

        if compressor_type == "rate":
            if not (0 < cr["value"] <= 1):
                raise ValueError(f"Error: 'value' in range {i+1} must be > 0 and ≤ 1 when compressor_type is 'rate'.")

        if compressor_type == "target_token":
            if not (isinstance(cr["value"], int) and cr["value"] > 0):
                raise ValueError(f"Error: 'value' in range {i+1} must be a positive integer when compressor_type is 'target_token'.")

def request_validation(data):
    text = data.get("text")
    if not (type(text) is list or type(text) is str):
        raise TypeError("No valid `text` found")

    messages = [ { "text": text, "msg_id": 1 } ] if type(text) is str else text
    
    model_name = data.get("model_name")
    if model_name is None:
        model_name = ""

    advanced_logging = data.get("advanced_logging")
    if advanced_logging is not None and not isinstance(advanced_logging, bool):
        raise ValueError("Error: 'advanced_logging' must be a boolean.")

    compressor_type = data.get("compressor_type")
    if compressor_type is None:
        raise ValueError("Error: You must provide 'compressor_type'.")
    if compressor_type not in ["rate", "target_token"]:
        raise ValueError(f"Error: 'compressor_type' must be 'rate' or 'target_token'.")

    compression_ranges = data.get("compression_ranges")
    validate_compression_ranges(compression_ranges, compressor_type)

    return {
        "messages": messages,
        "compressor_type": compressor_type,
        "compression_ranges": compression_ranges,
        "advanced_logging": advanced_logging,
        "model_name": model_name,
    }

def get_compression_value(token_count, compression_ranges):
    for range_ in compression_ranges:
        if token_count >= range_['min_tokens'] and token_count < range_['max_tokens']:
            return range_['value']
    return None

def do_compress_prompt(data, id=None):
    start_time = current_milli_time()
    messages = data.get("messages")
    compressor_type = data.get("compressor_type")
    compression_ranges = data.get("compression_ranges")
    model_name = data.get("model_name")
    advanced_logging = data.get("advanced_logging", False)

    compress_messages = []

    for message in messages:
        msg_id = message.get("msg_id")
        if not isinstance(msg_id, int):
            raise TypeError("No valid `msg_id` found")
        
        raw_content = message.get("text")
        if type(raw_content) != str:
            raise TypeError("`text` in the message is not string")

        # Check for <llmlingua ...>...</llmlingua> block
        llm_lingua_match = re.search(r"<LLMLINGUA[^>]*>(.*?)</LLMLINGUA>", raw_content, re.DOTALL)

        # Handle LLM Lingua section if it exists
        if llm_lingua_match:
            text_inside_tag = llm_lingua_match.group(1)
            raw_content_to_compress = text_inside_tag
        else:
            raw_content_to_compress = raw_content

        original_token_count = count_tokens(raw_content_to_compress, model_name)
        compression_value = get_compression_value(original_token_count, compression_ranges)

        if compression_value is None or (compressor_type == "target_token" and compression_value > original_token_count):

            message_to_append = {
                "compress_prompt": raw_content_to_compress,
                "compressor_results": {
                    "msg_id": msg_id,
                    "original_token_count": original_token_count,
                    "compress_token_count": 0,
                    "save_token_count": 0,
                    "information": "No compression was applied because the prompt is too short or its token count falls outside the defined compression ranges."

                },
                "msg_id": msg_id
            }

            if advanced_logging:
                message_to_append["compressor_results"]["original_text"] = raw_content_to_compress

            compress_messages.append(message_to_append)
            continue

        if not isinstance(original_token_count, int):
            raise ValueError(f"Token counting failed: {original_token_count}")

        # Clean the prompt
        raw_content_to_compress_stripped = strip_politeness(raw_content_to_compress)

        compressed = compress_text_f(raw_content_to_compress_stripped, compressor_type, compression_value)
        compress_text = compressed["compressed_prompt"]

        if compress_text is None:
            raise ValueError("Missing 'compressed_prompt' in result or error during compression")

        compress_token_count = count_tokens(compress_text, model_name)
        saved_tokens = original_token_count - compress_token_count

        if llm_lingua_match:
            # Replace the entire <LLMLINGUA>...</LLMLINGUA> section with compressed text in original raw_content
            compress_prompt = re.sub(
                r"<LLMLINGUA[^>]*>.*?</LLMLINGUA>",
                compress_text,
                raw_content,
                flags=re.DOTALL
            )
        else:
            # No LLM Lingua tag, so just use compressed text as is
            compress_prompt = compress_text

        message_to_append = {
            "compress_prompt": compress_prompt,
            "compressor_results": {
                "msg_id": msg_id,
                "original_token_count": original_token_count,
                "compress_token_count": compress_token_count,
                "save_token_count": saved_tokens,
                "compress_value": compression_value,
                "compress_type": compressor_type,
                "compressor_model": llmlingua_model_name_global,
                "information": f"Compression was performed and saved {saved_tokens} tokens",
            },
            "msg_id": msg_id
        }

        if advanced_logging:
            message_to_append["compressor_results"]["original_text"] = raw_content_to_compress
            message_to_append["compressor_results"]["compress_text"] = compress_text

        compress_messages.append(message_to_append)


    duration = current_milli_time() - start_time

    ret = {
        "text": compress_messages,
        "duration": duration
    }

    logging.info(f"--- Compression Request ---\n{json.dumps(data, indent=2)}")
    logging.info(f"--- Compression Response ---\n{json.dumps(ret, indent=2)}")

    if id is not None:
        return jsonrpc_response(ret, id)
    return jsonify(ret)

@app.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "ok", "model_name": llmlingua_model_name_global, "device_map": llmlingua_device_map_global}), 200

@app.route("/", methods=["POST"])
def rpc_router():
    logging.info(f"--- Raw Incoming Request to {request.path} ---\n{json.dumps(request.json, indent=2)}")
    data = request.json
    ok, err = validate_rpc_request(data)
    if not ok:
        return jsonrpc_error_response(err, data.get("id"))

    method = data.get("method")
    params = data.get("params")
    id = data.get("id")

    if method == method_prefix + "compressPrompt":
        try:
            data = request_validation(params)
            return do_compress_prompt(data, id)
        except Exception as e:
            return jsonrpc_error_response(str(e), id)
    else:
        return jsonrpc_error_response("Method not supported", id)


@app.route(path_prefix + "/compressPrompt", methods=["POST"])
def compress_direct():
    logging.info(f"--- Raw Incoming Request to {request.path} ---\n{json.dumps(request.json, indent=2)}")
    try:
        data = request_validation(request.json)
        return do_compress_prompt(data)
    except Exception as e:
        return jsonify({ "error": { "message": str(e) } }), 400


def cmdline_parser():
    parser = argparse.ArgumentParser(description="LLM Compression Service")
    parser.add_argument(
        "-p", "--port", type=int, default=8080, help="Port to run the server on"
    )
    parser.add_argument(
        "--log_level", type=str, default="info", choices=LOG_LEVELS.keys()
    )
    parser.add_argument(
        "-l",
        "--llmlingua_model_name",
        type=str,
        default=LLMLINGUA_MODEL_NAME_DEFAULT,
        help="The name of the LLM Lingua model to use (default: %s)" % LLMLINGUA_MODEL_NAME_DEFAULT,
    )
    parser.add_argument(
        "-d",
        "--llmlingua_device_map",
        type=str,
        default=LLMLINGUA_DEVICE_MAP_DEFAULT,
        help="The device map to use for the model (default: %s)" % LLMLINGUA_DEVICE_MAP_DEFAULT,
    )
    return parser

def main():
    parser = cmdline_parser()
    args = parser.parse_args()
    logging.basicConfig(level=LOG_LEVELS[args.log_level])
    try:
        init_globals(args.llmlingua_model_name, args.llmlingua_device_map)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1) 
    app.run(host="0.0.0.0", port=args.port)

if __name__ == "__main__":
    main()

elif __name__ == "ai_compress_service.server":
    llmlingua_model_name = os.getenv("LLMLINGUA_MODEL_NAME", LLMLINGUA_MODEL_NAME_DEFAULT)
    llmlingua_device_map = os.getenv("LLMLINGUA_DEVICE_MAP", LLMLINGUA_DEVICE_MAP_DEFAULT)
    log_level = os.getenv("LLMLINGUA_LOG_LEVEL", "info")
    logging.basicConfig(level=LOG_LEVELS.get(log_level, logging.INFO))
    try:
        init_globals(llmlingua_model_name, llmlingua_device_map)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
