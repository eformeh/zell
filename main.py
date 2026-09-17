import sys

from run import main


if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1].startswith("-"):
        sys.argv.insert(1, "data/raw_data.json")
    sys.exit(main())
