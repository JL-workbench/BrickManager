import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from brickmanager.recognition.brickognize import BrickognizeRecognizer


def main():
    parser = argparse.ArgumentParser(description="Test a local image with Brickognize")
    parser.add_argument("image", help="Path to a local image")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print("Brickognize Test")
    print("----------------")
    print(f"\nImage: {args.image}\n")

    result = BrickognizeRecognizer().identify_part(args.image)
    if not result.success:
        print(f"Brickognize API error:\n{result.error}")
        return 1
    if not result.best_match:
        print("No LEGO part detected.")
        return 0

    best = result.best_match
    print("Best match:")
    print(f"Part ID: {best.part_id}")
    print(f"Name: {best.name}")
    print(f"Confidence: {best.confidence:.2%}")
    if len(result.results) > 1:
        print("\nOther matches:")
        for index, match in enumerate(result.results[1:], start=1):
            print(f"{index}. {match.part_id} - {match.name} ({match.confidence:.2%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
