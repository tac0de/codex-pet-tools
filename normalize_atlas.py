"""Match the scale of each Codex v2 animation row to the idle row."""

import argparse
from pathlib import Path
from statistics import median

from PIL import Image


CELL_WIDTH = 192
CELL_HEIGHT = 208
COLUMNS = 8
STATES = (
    ("idle", 6),
    ("running-right", 8),
    ("running-left", 8),
    ("waving", 4),
    ("jumping", 5),
    ("failed", 8),
    ("waiting", 6),
    ("running", 6),
    ("review", 6),
    ("look-1", 8),
    ("look-2", 8),
)


def box(row, column):
    x, y = column * CELL_WIDTH, row * CELL_HEIGHT
    return x, y, x + CELL_WIDTH, y + CELL_HEIGHT


def face_width(frame, band):
    """Measure the widest opaque scanline in a band containing the cheeks."""
    top, bottom = band
    mask = frame.getchannel("A").point(lambda alpha: 255 if alpha >= 128 else 0)
    spans = [mask.crop((0, y, CELL_WIDTH, y + 1)).getbbox() for y in range(top, bottom)]
    return max((span[2] - span[0] for span in spans if span), default=0)


def atlas_rows(atlas, allow_intermediate=False):
    row_count = 9 if allow_intermediate and atlas.height == 9 * CELL_HEIGHT else len(STATES)
    expected_size = (COLUMNS * CELL_WIDTH, row_count * CELL_HEIGHT)
    if atlas.size != expected_size:
        raise ValueError(f"expected a Codex atlas of size {expected_size}")

    for row, (state, count) in enumerate(STATES[:row_count]):
        cells = [atlas.crop(box(row, column)) for column in range(COLUMNS)]
        bounds = [cell.getbbox() for cell in cells]
        # Extended sheets may have a neutral look pose in idle column 7.
        has_neutral_slot = row == 0 and row_count == len(STATES)
        unused = bounds[count + int(has_neutral_slot):]
        if not all(bounds[:count]) or any(unused):
            raise ValueError(f"{state} has missing or unexpected frames")
        yield row, state, cells[:count], bounds[:count]


def normalize(atlas, bands, resampling, target_width=None, baseline=None):
    if target_width is not None or baseline is not None:
        if atlas.height != 9 * CELL_HEIGHT or set(bands) != {state for state, _ in STATES[:9]}:
            raise ValueError("target width and baseline require all nine bands on a standard-row intermediate")
    output = atlas.copy()
    reference_width = reference_floor = None
    for row, state, cells, bounds in atlas_rows(atlas, allow_intermediate=True):
        if state not in bands:
            continue

        widths = [face_width(cell, bands[state]) for cell in cells]
        if not all(widths):
            raise ValueError(f"{state} has a frame with no opaque pixels in its face band")
        width = median(widths)
        floor = max(bound[3] for bound in bounds)
        if row == 0:
            reference_width = target_width if target_width is not None else width
            reference_floor = baseline if baseline is not None else floor
            if target_width is None and baseline is None:
                continue

        factor = reference_width / width
        print(f"{state}: {width:g} px → {reference_width:g} px ({factor:.3f}×)")
        for column, (cell, bound) in enumerate(zip(cells, bounds)):
            left, top, right, bottom = bound
            crop = cell.crop(bound)
            size = max(1, round(crop.width * factor)), max(1, round(crop.height * factor))
            x = round(CELL_WIDTH / 2 + (left - CELL_WIDTH / 2) * factor)
            y = (reference_floor + bottom - floor) - size[1]
            if x < 0 or y < 0 or x + size[0] > CELL_WIDTH or y + size[1] > CELL_HEIGHT:
                raise ValueError(f"{state} frame {column + 1} would be clipped")
            normalized = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT))
            normalized.paste(crop.resize(size, resampling), (x, y))
            output.paste(normalized, box(row, column))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--band", action="append", required=True, metavar="STATE:TOP:BOTTOM")
    parser.add_argument("--target-width", type=int, help="set the face width in pixels, including idle")
    parser.add_argument("--baseline", type=int, help="set the lowest bottom edge in pixels, including idle")
    parser.add_argument("--pixel-art", action="store_true", help="use nearest-neighbor sampling")
    args = parser.parse_args()
    bands = {}
    states = dict(STATES[:9])
    try:
        for spec in args.band:
            state, top, bottom = spec.split(":")
            band = int(top), int(bottom)
            if state not in states or state in bands or not 0 <= band[0] < band[1] <= CELL_HEIGHT:
                raise ValueError(f"invalid or duplicate band: {spec}")
            bands[state] = band
        if "idle" not in bands or len(bands) < 2:
            raise ValueError("specify a band for idle and at least one animation state")
        if args.target_width is not None and not 1 <= args.target_width <= CELL_WIDTH:
            raise ValueError("target width must be between 1 and 192 px")
        if args.baseline is not None and not 1 <= args.baseline <= CELL_HEIGHT:
            raise ValueError("baseline must be between 1 and 208 px")
        if args.input.resolve() == args.output.resolve():
            raise ValueError("choose a separate output path")
        resampling = Image.Resampling.NEAREST if args.pixel_art else Image.Resampling.LANCZOS
        with Image.open(args.input) as source:
            output = normalize(source.convert("RGBA"), bands, resampling, args.target_width, args.baseline)
        if args.output.suffix.lower() == ".webp":
            output.save(args.output, format="WEBP", lossless=True, exact=True)
        elif args.output.suffix.lower() == ".png":
            output.save(args.output, format="PNG")
        else:
            raise ValueError("output must be .webp or .png")
    except (ValueError, OSError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
