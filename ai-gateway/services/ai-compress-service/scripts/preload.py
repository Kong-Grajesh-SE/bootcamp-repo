import tiktoken, os

ENCODINGS = ["gpt2", "r50k_base", "p50k_base", "p50k_edit", "cl100k_base", "o200k_base", "o200k_harmony"]
cache_dir = os.environ["TIKTOKEN_CACHE_DIR"]
for encoding in ENCODINGS:
  tiktoken.get_encoding(encoding)