# FinBERT Tokenizer Setup Instructions

You have successfully downloaded the FinBERT model files (config.json and pytorch_model.bin), but you're missing the tokenizer files needed to use the model.

## Option 1: Download Files Manually

Download these 4 files from HuggingFace and save them to:
`d:\workspace\projects\Stocks\stockiq\models\sentiment\FinBERT\`

### Files to Download:

1. **vocab.txt** (226 KB)
   - URL: https://huggingface.co/ProsusAI/finbert/resolve/main/vocab.txt
   - Right-click → Save As → `vocab.txt`

2. **tokenizer_config.json** (0.3 KB)
   - URL: https://huggingface.co/ProsusAI/finbert/resolve/main/tokenizer_config.json
   - Right-click → Save As → `tokenizer_config.json`

3. **special_tokens_map.json** (0.1 KB)
   - URL: https://huggingface.co/ProsusAI/finbert/resolve/main/special_tokens_map.json
   - Right-click → Save As → `special_tokens_map.json`

4. **tokenizer.json** (466 KB)
   - URL: https://huggingface.co/ProsusAI/finbert/resolve/main/tokenizer.json
   - Right-click → Save As → `tokenizer.json`

## Option 2: Use HuggingFace CLI (if you have it)

```bash
cd stockiq\models\sentiment\FinBERT
huggingface-cli download ProsusAI/finbert vocab.txt tokenizer_config.json special_tokens_map.json tokenizer.json
```

## Option 3: Let the System Download Tokenizer Automatically

If you don't download the tokenizer files, the system will automatically download them from HuggingFace when you first use the sentiment analyzer. It uses your local model file but downloads the tokenizer from online.

This "hybrid" approach is what the updated code does:
- **Model**: Loaded from local path (417 MB - already downloaded)
- **Tokenizer**: Downloaded from HuggingFace (~700 KB - small download)

## Verification

After downloading the tokenizer files (or letting the system auto-download), verify with:

```python
from stockiq.news.nlp.sentiment import get_sentiment_analyzer

analyzer = get_sentiment_analyzer()
result = analyzer.analyze_sentiment("Apple reports record-breaking quarterly earnings!")

print(f"Overall: {result.overall:.3f}")
print(f"VADER: {result.vader_score:.3f}")
print(f"FinBERT: {result.finbert_score:.3f}")
print(f"Confidence: {result.confidence:.3f}")
```

Expected output (with FinBERT working):
```
Overall: 0.650
VADER: 0.567
FinBERT: 0.708
Confidence: 0.814
```

## Current Status

✅ **VADER** - Working (rule-based sentiment)
✅ **FinBERT Model** - Downloaded (417 MB)
❌ **FinBERT Tokenizer** - Missing (needs 4 files, ~700 KB total)

The sentiment analyzer will work with VADER-only mode until tokenizer files are available.
