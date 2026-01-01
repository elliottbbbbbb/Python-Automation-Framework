# Documentation

This directory contains setup guides and technical documentation for the OSRS Bot Framework.

## Setup Guides

### [SETUP.md](SETUP.md)
Main setup guide for the OSRS Bot Framework. Covers:
- Installation requirements
- RuneLite configuration
- Bot configuration
- Running your first bot

### [INTERCEPTION_SETUP.md](INTERCEPTION_SETUP.md)
Guide for setting up kernel-level mouse control using the Interception driver. Covers:
- Installing the Interception driver
- Installing interception-python package
- Configuring the bot to use Interception
- Troubleshooting Interception issues

**Benefits of Interception:**
- Hardware-level mouse input (appears as real USB mouse)
- Better anti-detection compared to software mouse control
- Works with games that block software input

---

## Technical Documentation

### [OCR_IMPROVEMENTS_SUMMARY.md](OCR_IMPROVEMENTS_SUMMARY.md)
Summary of OCR improvements and testing results. Covers:
- Template Matching OCR implementation (kellton's approach)
- Comparison with Tesseract OCR
- Performance benchmarks
- Testing methodology
- Known issues and solutions

**Key Findings:**
- Template Matching: ~99% accuracy, ~2ms speed
- Tesseract: ~90-95% accuracy, ~100ms+ speed
- Template Matching eliminates 4/9 confusion

---

## Quick Links

- **Main README:** [../README.md](../README.md)
- **Manual Test Scripts:** [../tests/manual/README.md](../tests/manual/README.md)
- **Examples:** [../examples/](../examples/)

---

## Contributing

When adding new documentation:
1. Place setup guides in this directory
2. Use clear, descriptive filenames
3. Update this README with a brief description
4. Link related documentation where appropriate
