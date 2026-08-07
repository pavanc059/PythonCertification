"""
Copy vocab.txt from BERT base (if cached) to FinBERT directory.
"""

import os
import shutil
from pathlib import Path

try:
    from transformers import BertTokenizer
    
    print("Attempting to load BERT tokenizer from cache...")
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
    
    vocab_file = tokenizer.vocab_file
    print(f"Found vocab file at: {vocab_file}")
    print(f"Exists: {os.path.exists(vocab_file)}")
    
    if os.path.exists(vocab_file):
        dest = Path(__file__).parent / "stockiq" / "models" / "sentiment" / "FinBERT" / "vocab.txt"
        shutil.copy(vocab_file, dest)
        print(f"\n✓ Successfully copied vocab.txt to: {dest}")
        print(f"  File size: {dest.stat().st_size / 1024:.1f} KB")
    else:
        print("✗ Vocab file not found")
        
except Exception as e:
    print(f"✗ Failed: {e}")
    print("\nThis means BERT tokenizer needs to be downloaded first.")
    print("The script will download it now (this may take a moment due to SSL issues)...")
