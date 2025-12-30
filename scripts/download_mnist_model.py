"""
Download and prepare a pre-trained MNIST CNN model for digit classification.

This script downloads a lightweight ONNX model trained on MNIST dataset
and saves it to the models/ directory.
"""
import os
import urllib.request
from pathlib import Path

# URLs for pre-trained MNIST models (ONNX format)
MODEL_URLS = {
    "mnist_cnn": "https://github.com/onnx/models/raw/main/validated/vision/classification/mnist/model/mnist-8.onnx"
}


def download_model(url: str, output_path: Path) -> bool:
    """
    Download a model from URL.

    Args:
        url: Model URL
        output_path: Path to save the model

    Returns:
        True if successful
    """
    try:
        print(f"Downloading model from {url}...")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with urllib.request.urlopen(url) as response:
            with open(output_path, 'wb') as f:
                f.write(response.read())

        print(f"Model saved to {output_path}")
        print(f"Model size: {output_path.stat().st_size / 1024:.1f} KB")
        return True

    except Exception as e:
        print(f"Failed to download model: {e}")
        return False


def main():
    """Download MNIST model."""
    print("=" * 60)
    print("MNIST MODEL DOWNLOADER")
    print("=" * 60)

    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    models_dir = project_root / "src" / "osrsbot" / "models"

    # Download CNN model
    model_path = models_dir / "mnist_cnn.onnx"

    if model_path.exists():
        print(f"\nModel already exists at {model_path}")
        response = input("Re-download? (y/N): ").strip().lower()
        if response != 'y':
            print("Skipping download.")
            return

    print(f"\nDownloading to: {model_path}")
    success = download_model(MODEL_URLS["mnist_cnn"], model_path)

    if success:
        print("\n" + "=" * 60)
        print("DOWNLOAD COMPLETE")
        print("=" * 60)
        print("\nThe digit classifier is now ready to use!")
        print("It will automatically be used instead of Tesseract OCR.")
    else:
        print("\n" + "=" * 60)
        print("DOWNLOAD FAILED")
        print("=" * 60)
        print("\nThe bot will fall back to Tesseract OCR.")


if __name__ == "__main__":
    main()
