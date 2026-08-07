"""
Download FinBERT tokenizer files to local directory.

This script downloads only the tokenizer files (vocab.txt, tokenizer_config.json, etc.)
from HuggingFace and saves them to the local FinBERT model directory.
"""

import os
import ssl
import urllib.request
from pathlib import Path

# Disable SSL verification (for corporate proxies)
ssl._create_default_https_context = ssl._create_unverified_context

# Local FinBERT model directory
FINBERT_DIR = Path(__file__).parent / "stockiq" / "models" / "sentiment" / "FinBERT"
FINBERT_DIR.mkdir(parents=True, exist_ok=True)

# HuggingFace model URL
BASE_URL = "https://huggingface.co/ProsusAI/finbert/resolve/main"

# Files to download
TOKENIZER_FILES = [
    "vocab.txt",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "tokenizer.json"
]

def download_file(filename):
    """Download a file from HuggingFace."""
    url = f"{BASE_URL}/{filename}"
    output_path = FINBERT_DIR / filename
    
    print(f"Downloading {filename}...", end=" ")
    try:
        urllib.request.urlretrieve(url, output_path)
        print(f"✓ Saved to {output_path}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

def main():
    """Download all tokenizer files."""
    print(f"FinBERT Model Directory: {FINBERT_DIR}\n")
    
    # Check existing files
    print("Existing files:")
    for f in FINBERT_DIR.glob("*"):
        print(f"  - {f.name}")
    print()
    
    # Download tokenizer files
    print("Downloading tokenizer files from HuggingFace...\n")
    
    success_count = 0
    for filename in TOKENIZER_FILES:
        if download_file(filename):
            success_count += 1
    
    print(f"\n✓ Downloaded {success_count}/{len(TOKENIZER_FILES)} files successfully!")
    
    # List all files
    print("\nAll files in FinBERT directory:")
    for f in sorted(FINBERT_DIR.glob("*")):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  - {f.name} ({size_mb:.2f} MB)")

if __name__ == "__main__":
    main()
