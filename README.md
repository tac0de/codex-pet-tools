# Codex Pet Tools

Normalize the apparent size of a local Codex v2 pet across animation states. Use a horizontal band through the face in each state to estimate scale, even when ears, limbs, or props make the full silhouette larger or smaller.

## Usage

Install Python 3 and Pillow, then run the tool on your own PNG or WebP sheet.

```sh
python3 -m pip install 'Pillow>=10'
python3 normalize_atlas.py original.webp normalized.webp --pixel-art \
  --band idle:95:144 \
  --band jumping:83:144 \
  --band failed:95:148
```

The example band coordinates are relative to each 192 × 208 cell, with an inclusive top and exclusive bottom. Adjust the bands for your character and poses. Include the widest part of the face and exclude wider limbs, props, or disconnected effects. Use `--pixel-art` for nearest-neighbor sampling. The default uses Lanczos.

The median face width in the idle row sets the target. Each specified state receives one uniform scale across all of its frames. The lowest bottom edge in that row aligns with the lowest idle bottom edge. Relative vertical displacement is preserved in pixels, including jump height. The tool rejects a transform that would clip a frame. Idle, both look rows, and any unlisted state pass through unchanged.

The input can be a transparent 1536 × 2288 Codex v2 sheet or a 1536 × 1872 intermediate with the nine standard rows. To set a common scale and ground line across a collection, pass `--target-width` and `--baseline` on an intermediate and provide a band for all nine rows. Then register the two look rows against the new idle frame before packaging. The output is a separate PNG or lossless WebP. Preview the transition between idle and the adjusted states before installing. See the [Codex pet contract](https://github.com/openai/skills/blob/main/skills/.curated/hatch-pet/references/codex-pet-contract.md).

## Package a validated sheet

```sh
python3 pack_pet.py normalized.webp packages --id my-pet --name "My Pet"
```

This creates `packages/my-pet/` with a manifest and the same sheet bytes. The packer checks dimensions, frame placement, and transparency. Validate motion, direction semantics, and color edges separately. Copy the package into `${CODEX_HOME:-$HOME/.codex}/pets/` when ready to use it in Codex.

## License

MIT for the tool source. Character artwork and generated sprite sheets are outside the repository.
