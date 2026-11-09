"""Align the look rows and the optional neutral look pose with the idle baseline."""

import argparse
from pathlib import Path
from statistics import median

from PIL import Image

from normalize_atlas import box, atlas_rows, save_atlas


def align_look(atlas):
    rows = list(atlas_rows(atlas))
    idle_floor = max(bound[3] for bound in rows[0][3])
    look_cells = [(box(row, column), cell, bound)
                  for row, _, cells, bounds in rows[9:]
                  for column, (cell, bound) in enumerate(zip(cells, bounds))]
    neutral_box = box(0, 6)
    neutral = atlas.crop(neutral_box)
    neutral_bounds = neutral.getbbox()
    if neutral_bounds:
        look_cells.append((neutral_box, neutral, neutral_bounds))
        look_floor = neutral_bounds[3]
    else:
        look_floor = round(median(bound[3] for _, _, bound in look_cells))

    offset = idle_floor - look_floor
    output = atlas.copy()
    for area, cell, bound in look_cells:
        if not 0 <= bound[1] + offset or bound[3] + offset > cell.height:
            raise ValueError("moving the look rows would clip a pose")
        shifted = Image.new("RGBA", cell.size)
        shifted.paste(cell.crop(bound), (bound[0], bound[1] + offset))
        output.paste(shifted, area)
    return output, offset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        if args.input.resolve() == args.output.resolve():
            raise ValueError("choose a separate output path")
        with Image.open(args.input) as source:
            output, offset = align_look(source.convert("RGBA"))
        save_atlas(output, args.output)
        print(f"Look rows moved vertically by {offset:+d} px")
    except (ValueError, OSError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
