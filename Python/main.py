"""
Main entry point for XAU_AI_PRO.
Usage:
    python main.py predict
    python main.py train
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def main():
    if len(sys.argv) < 2:
        print("No command provided. Defaulting to: train")
        arg = "train"
    else:
        arg = sys.argv[1].lower()

    if arg == "predict":
        # Load and run predict module
        import importlib.util

        predict_path = BASE_DIR / "predict.py"
        spec = importlib.util.spec_from_file_location("predict", predict_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.predict()
        else:
            print(f"Failed to load {predict_path}")
            sys.exit(1)

    elif arg == "train":
        # Load and run train module
        import importlib.util

        train_path = BASE_DIR / "train.py"
        spec = importlib.util.spec_from_file_location("train", train_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.train()
        else:
            print(f"Failed to load {train_path}")
            sys.exit(1)

    else:
        print(f"Unknown command: {arg}")
        print("Usage: python main.py [predict|train]")
        sys.exit(1)


if __name__ == "__main__":
    main()
