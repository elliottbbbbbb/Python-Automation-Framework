"""Diagnose why 9 is being detected as 4."""

import sys

from PIL import Image

from osrsbot.services.ocr_service import OCRService
from osrsbot.utils.ocr_helpers import (
    count_holes_and_tail,
    looks_like_nine,
    preprocess_for_shape_detection,
)


def diagnose_nine(image_path: str):
    """
    Diagnose 9 vs 4 detection issues.

    Args:
        image_path: Path to image containing a '9' that's being misread as '4'
    """
    print("=" * 70)
    print("9 vs 4 DIAGNOSTIC TOOL")
    print("=" * 70)

    try:
        img = Image.open(image_path)
        print(f"\nLoaded image: {image_path}")
        print(f"Size: {img.width}x{img.height}")
        print("-" * 70)

        # Create OCR service
        ocr = OCRService(debug=True, use_cnn=False)

        # Generate all preprocessing strategies
        print("\n[1] GENERATING PREPROCESSING STRATEGIES")
        strategies = ocr._preprocess_for_numbers(img)
        print(f"    Generated {len(strategies)} strategies")

        # Test each strategy with OCR
        print("\n[2] OCR RESULTS PER STRATEGY")
        import re

        import pytesseract

        from osrsbot.constants import TESSERACT_CONFIG

        all_results = []
        for i, strategy_img in enumerate(strategies):
            try:
                text = pytesseract.image_to_string(
                    strategy_img, config=TESSERACT_CONFIG.get_config_string()
                )
                cleaned = text.strip()
                numbers = re.findall(r"\d+", cleaned)
                result = int(numbers[0]) if numbers else None
                all_results.append(result)
                print(f"    Strategy {i}: '{cleaned}' -> {result}")
            except Exception as e:
                all_results.append(None)
                print(f"    Strategy {i}: FAILED ({e})")

        # Show consensus
        from collections import Counter

        valid_results = [r for r in all_results if r is not None]
        if valid_results:
            consensus = Counter(valid_results).most_common(1)[0][0]
            print(f"\n    OCR Consensus: {consensus}")
        else:
            consensus = None
            print(f"\n    OCR Consensus: NONE")

        # Test shape detection on each strategy
        print("\n[3] SHAPE DETECTION ANALYSIS")
        nine_votes = 0
        for i, strategy_img in enumerate(strategies):
            try:
                # Preprocess for shape detection
                bw = preprocess_for_shape_detection(strategy_img, size=(140, 140))
                hole_count, tail_frac, aspect = count_holes_and_tail(bw)

                # Check if looks like 9
                is_nine = looks_like_nine(strategy_img)
                if is_nine:
                    nine_votes += 1

                print(
                    f"    Strategy {i}: holes={hole_count}, tail={tail_frac:.3f}, "
                    f"aspect={aspect:.3f}, is_nine={is_nine}"
                )
            except Exception as e:
                print(f"    Strategy {i}: Shape detection failed - {e}")

        print(f"\n    Total '9' votes: {nine_votes}/{len(strategies)}")

        # Check if it would be corrected
        print("\n[4] CORRECTION LOGIC")
        from osrsbot.constants import SHAPE_DETECTION

        threshold_met = nine_votes >= SHAPE_DETECTION.min_nine_votes_for_correction
        ocr_agrees = (
            SHAPE_DETECTION.trust_ocr_with_single_vote
            and nine_votes >= 1
            and 9 in valid_results
        )

        print(
            f"    Threshold met ({nine_votes} >= {SHAPE_DETECTION.min_nine_votes_for_correction}): {threshold_met}"
        )
        print(
            f"    OCR agrees (votes={nine_votes}, 9 in results={9 in valid_results}): {ocr_agrees}"
        )

        if consensus == 4:
            if threshold_met or ocr_agrees:
                final_result = 9
                print(f"\n    FINAL: Would correct 4 -> 9 ✓")
            else:
                final_result = 4
                print(f"\n    FINAL: Would NOT correct (stays as 4) ✗")
        else:
            final_result = consensus
            print(f"\n    FINAL: No correction needed (OCR returned {consensus})")

        # Recommendations
        print("\n" + "=" * 70)
        print("RECOMMENDATIONS")
        print("=" * 70)

        if final_result == 4 and nine_votes > 0:
            print("\n⚠ ISSUE: OCR returning 4 but shape detection found 9 features")
            print("\nPossible solutions:")
            print(
                f"  1. Lower min_nine_votes_for_correction (current: {SHAPE_DETECTION.min_nine_votes_for_correction})"
            )
            print(
                "  2. Adjust shape detection thresholds (hole_count, tail_frac, aspect)"
            )
            print("  3. Improve preprocessing to preserve 9's circular feature")
            print("  4. Use CNN classifier instead (more accurate for OSRS fonts)")
        elif final_result == 9 and nine_votes == 0:
            print("\n✓ GOOD: OCR correctly detected 9")
        elif final_result == 4 and nine_votes == 0:
            print("\n✓ CORRECT: This is actually a 4, not a 9")
        else:
            print(f"\n✓ Result: {final_result}")

        # Show shape detection config
        print("\n" + "-" * 70)
        print("CURRENT SHAPE DETECTION CONFIG:")
        print(
            f"  min_nine_votes_for_correction: {SHAPE_DETECTION.min_nine_votes_for_correction}"
        )
        print(
            f"  trust_ocr_with_single_vote: {SHAPE_DETECTION.trust_ocr_with_single_vote}"
        )
        print(f"  min_hole_count_for_nine: {SHAPE_DETECTION.min_hole_count_for_nine}")
        print(
            f"  min_tail_fraction_for_nine: {SHAPE_DETECTION.min_tail_fraction_for_nine}"
        )
        print(
            f"  min_aspect_ratio_for_nine: {SHAPE_DETECTION.min_aspect_ratio_for_nine}"
        )

    except FileNotFoundError:
        print(f"ERROR: Could not find image at: {image_path}")
        print("\nUsage:")
        print("  python diagnose_nine_detection.py <image_path>")
        print("\nExample:")
        print("  python diagnose_nine_detection.py ocr_debug/hp_strategy_0.png")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_nine_detection.py <image_path>")
        print("\nExample:")
        print("  python diagnose_nine_detection.py ocr_debug/hp_strategy_0.png")
        print("\nThis will show why '9' is being detected as '4' and suggest fixes.")
    else:
        diagnose_nine(sys.argv[1])
