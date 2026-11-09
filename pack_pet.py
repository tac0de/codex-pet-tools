"""Create a local Codex v2 pet package from a validated sprite sheet."""

import argparse
from io import BytesIO
import json
from pathlib import Path
import re
import tempfile

from PIL import Image

from normalize_atlas import atlas_rows


def pack(source, output_root, pet_id, name, description):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", pet_id):
        raise ValueError("pet ID must be lowercase alphanumeric words separated by hyphens")
    data = source.read_bytes()
    with Image.open(BytesIO(data)) as image:
        extension = {"PNG": ".png", "WEBP": ".webp"}.get(image.format)
        if not extension or getattr(image, "n_frames", 1) != 1:
            raise ValueError("expected a static PNG or WebP sheet")
        for _, state, cells, _ in atlas_rows(image.convert("RGBA")):
            if any(cell.getchannel("A").getextrema()[0] != 0 for cell in cells):
                raise ValueError(f"{state} contains a frame without transparency")

    filename = "spritesheet" + extension
    manifest = {
        "id": pet_id,
        "displayName": name,
        "description": description,
        "spriteVersionNumber": 2,
        "spritesheetPath": filename,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    destination = output_root / pet_id
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"package already exists: {destination}")

    with tempfile.TemporaryDirectory(prefix=".pet-stage-", dir=output_root) as scratch:
        stage = Path(scratch) / pet_id
        stage.mkdir()
        (stage / filename).write_bytes(data)
        (stage / "pet.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        stage.rename(destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sheet", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--description", default="")
    args = parser.parse_args()
    try:
        print(pack(args.sheet, args.output_root, args.id, args.name, args.description))
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
