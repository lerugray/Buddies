"""Render buddy sprites as animated GIFs for the README.

Reads the raw pixel data from sprites.py and creates scaled-up
animated GIFs using Pillow. Each species gets a looping 4-frame GIF.
"""

import sys
import os

# Add the project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PIL import Image

# Color palette (same as sprites.py but as RGB tuples)
COLORS = {
    "k": (0, 0, 0),
    "w": (255, 255, 255),
    "r": (255, 0, 68),
    "R": (170, 0, 34),
    "o": (255, 136, 0),
    "O": (204, 85, 0),
    "y": (255, 221, 0),
    "Y": (204, 170, 0),
    "g": (68, 221, 68),
    "G": (34, 136, 34),
    "b": (68, 136, 255),
    "B": (34, 68, 170),
    "c": (68, 221, 221),
    "C": (34, 136, 136),
    "p": (221, 68, 221),
    "P": (136, 34, 136),
    "n": (255, 204, 170),
    "N": (204, 153, 102),
    "e": (136, 136, 136),
    "E": (68, 68, 68),
    "t": None,  # transparent
}

# Background color for transparent pixels
BG_COLOR = (24, 24, 32)  # Dark terminal-like background


def get_frame_rows(species_name: str) -> list[list[str]]:
    """Extract raw row data for each frame of a species.

    Returns list of frames, each frame is a list of color-code strings.
    """
    # Import the sprites module to get the frame functions
    import buddies.art.sprites as sprites_mod
    import inspect

    # Find the frame function for this species
    func_name = f"_{species_name}_frames"
    func = getattr(sprites_mod, func_name, None)
    if not func:
        print(f"No frame function found for {species_name}")
        return []

    # Get the source and extract the row data
    # We need to parse the _build_sprite calls from the source
    source = inspect.getsource(func)

    frames = []
    # Parse each _build_sprite([...]) call
    import re
    # Find all _build_sprite calls and extract their row lists
    pattern = r'_build_sprite\(\[\s*((?:"[^"]*",?\s*)*)\]\)'
    matches = re.findall(pattern, source)

    for match in matches:
        # Extract individual row strings
        row_pattern = r'"([^"]*)"'
        rows = re.findall(row_pattern, match)
        if rows:
            frames.append(rows)

    return frames


def render_frame(rows: list[str], scale: int = 8) -> Image.Image:
    """Render a single frame to a Pillow Image.

    Each character = 1 pixel. Scaled up by `scale` factor.
    """
    if not rows:
        return Image.new("RGBA", (1, 1))

    height = len(rows)
    width = max(len(r) for r in rows)

    img = Image.new("RGBA", (width * scale, height * scale), (*BG_COLOR, 255))

    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            color = COLORS.get(char)
            if color is None:
                continue  # transparent
            # Fill the scaled pixel
            for dy in range(scale):
                for dx in range(scale):
                    img.putpixel((x * scale + dx, y * scale + dy), (*color, 255))

    return img


def create_animated_gif(
    species_name: str,
    output_path: str,
    scale: int = 8,
    frame_duration: int = 500,
):
    """Create an animated GIF for a species."""
    frame_rows = get_frame_rows(species_name)
    if not frame_rows:
        print(f"No frames found for {species_name}")
        return False

    frames = []
    for rows in frame_rows:
        img = render_frame(rows, scale=scale)
        frames.append(img)

    if not frames:
        return False

    # Save as animated GIF
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=frame_duration,
        loop=0,  # infinite loop
        disposal=2,  # clear between frames
    )
    print(f"  Created {output_path} ({len(frames)} frames, {frames[0].size[0]}x{frames[0].size[1]})")
    return True


def main():
    # Showcase species — one from each rarity
    showcase = [
        ("phoenix", "Epic"),
        ("dragon", "Rare"),
        ("cat", "Common"),
        ("zorak", "Legendary"),
        ("corgi", "Common"),
        ("frog", "Common"),
    ]

    output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
    os.makedirs(output_dir, exist_ok=True)

    print("Rendering sprite GIFs...")
    for species, rarity in showcase:
        path = os.path.join(output_dir, f"buddy-{species}.gif")
        success = create_animated_gif(species, path, scale=8, frame_duration=500)
        if success:
            print(f"  OK: {species} ({rarity})")
        else:
            print(f"  FAIL: {species} — failed")

    # Also create a combined banner with multiple buddies side by side
    print("\nRendering combined banner...")
    banner_species = ["phoenix", "cat", "dragon", "frog", "corgi"]
    banner_frames = []
    for sp in banner_species:
        rows = get_frame_rows(sp)
        if rows:
            banner_frames.append(rows)

    if banner_frames:
        scale = 6
        padding = 4  # pixels between sprites
        max_height = max(len(f[0]) for f in banner_frames) * scale
        total_width = sum(max(len(r) for r in f[0]) * scale for f in banner_frames) + padding * scale * (len(banner_frames) - 1)

        # Create 4 banner frames (cycling all sprites together)
        banner_gifs = []
        for frame_idx in range(4):
            img = Image.new("RGBA", (total_width, max_height), (*BG_COLOR, 255))
            x_offset = 0
            for sp_frames in banner_frames:
                f_idx = frame_idx % len(sp_frames)
                rows = sp_frames[f_idx]
                sprite_w = max(len(r) for r in rows) * scale
                sprite_h = len(rows) * scale
                sprite_img = render_frame(rows, scale=scale)
                # Center vertically
                y_offset = (max_height - sprite_h) // 2
                img.paste(sprite_img, (x_offset, y_offset))
                x_offset += sprite_w + padding * scale
            banner_gifs.append(img)

        banner_path = os.path.join(output_dir, "buddy-banner.gif")
        banner_gifs[0].save(
            banner_path,
            save_all=True,
            append_images=banner_gifs[1:],
            duration=600,
            loop=0,
            disposal=2,
        )
        print(f"  OK: Banner: {banner_path}")


if __name__ == "__main__":
    main()
