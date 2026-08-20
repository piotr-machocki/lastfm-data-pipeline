from pathlib import Path

SOURCE_DIR = Path("src")
OUTPUT_FILE = Path("all_code.txt")


with OUTPUT_FILE.open("w", encoding="utf-8") as output:
    for file in sorted(SOURCE_DIR.iterdir()):
        if file.is_file() and file.suffix == ".py":
            output.write(f"\n{'=' * 60}\n")
            output.write(f"# {file.name}\n")
            output.write(f"{'=' * 60}\n\n")

            output.write(file.read_text(encoding="utf-8"))
            output.write("\n\n")