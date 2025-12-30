# Neural Network Models

This directory contains pre-trained neural network models used by the bot.

## MNIST Digit Classifier

The bot uses a lightweight CNN model trained on MNIST for digit recognition in OCR tasks.

### Download the Model

Run this command from the project root:

```bash
python scripts/download_mnist_model.py
```

This will download `mnist_cnn.onnx` (~26KB) to this directory.

### Why Use a Neural Network Instead of Tesseract?

1. **99%+ Accuracy** - CNN models are trained specifically for digit recognition
2. **Fast** - ~0.1ms per digit on CPU (faster than Tesseract)
3. **Reliable** - No confusion between 9 and 4, or other similar digits
4. **Small** - Only 26KB model file
5. **No Dependencies** - Works with ONNX Runtime (already installed)

### Fallback

If the model is not available, the bot will automatically fall back to Tesseract OCR with shape-based heuristics.

## Model Details

- **File**: `mnist_cnn.onnx`
- **Size**: 25.8 KB
- **Format**: ONNX (Open Neural Network Exchange)
- **Input**: 28x28 grayscale image
- **Output**: 10 classes (digits 0-9)
- **Accuracy**: 99%+ on MNIST test set
