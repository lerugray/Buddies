"""Colored 8-bit pixel art sprites using Unicode half-blocks and Rich markup.

Each sprite is a list of animation frames. Frames use Rich markup for color:
  [red]██[/] = red pixels
  [#FF8800 on #442200]▀[/] = orange top pixel, brown bottom pixel

Half-block technique: ▀ (upper half) lets us pack 2 pixel rows per text line.
This gives actual pixel-art resolution in the terminal.
"""

from __future__ import annotations


# Color palette — retro 8-bit style
C = {
    "k": "#000000",   # black
    "w": "#FFFFFF",   # white
    "r": "#FF0044",   # red
    "R": "#AA0022",   # dark red
    "o": "#FF8800",   # orange
    "O": "#CC5500",   # dark orange
    "y": "#FFDD00",   # yellow
    "Y": "#CCAA00",   # dark yellow
    "g": "#44DD44",   # green
    "G": "#228822",   # dark green
    "b": "#4488FF",   # blue
    "B": "#2244AA",   # dark blue
    "c": "#44DDDD",   # cyan
    "C": "#228888",   # dark cyan
    "p": "#DD44DD",   # pink/magenta
    "P": "#882288",   # dark purple
    "n": "#FFCCAA",   # skin/tan
    "N": "#CC9966",   # dark tan
    "e": "#888888",   # gray
    "E": "#444444",   # dark gray
    "t": "",          # transparent (no color)
}


def _px(top: str, bot: str) -> str:
    """Create a half-block pixel with top and bottom colors.

    Uses ▀ (upper half block) with foreground=top, background=bottom.
    If both transparent, return a space.
    """
    tc = C.get(top, "")
    bc = C.get(bot, "")

    if not tc and not bc:
        return " "
    if not tc:
        return f"[on {bc}] [/]"
    if not bc:
        return f"[{tc}]▀[/]"
    if tc == bc:
        return f"[{tc}]█[/]"
    return f"[{tc} on {bc}]▀[/]"


def _build_sprite(rows: list[str]) -> str:
    """Build a sprite from a grid of color codes.

    Each character in a row is a color key from the palette.
    Rows are paired top/bottom for half-block rendering.
    Pad to even number of rows if needed.
    """
    if len(rows) % 2 != 0:
        rows = rows + ["t" * len(rows[0])]

    lines = []
    for i in range(0, len(rows), 2):
        top_row = rows[i]
        bot_row = rows[i + 1]
        # Pad to same length
        max_len = max(len(top_row), len(bot_row))
        top_row = top_row.ljust(max_len, "t")
        bot_row = bot_row.ljust(max_len, "t")
        line = "".join(_px(t, b) for t, b in zip(top_row, bot_row))
        lines.append(line)

    return "\n".join(lines)


# ============================================================
# SPECIES SPRITES — 8-bit pixel art
# Each species has 2+ frames for idle animation
# Grid is roughly 12-16 wide, 12-16 tall
# ============================================================

def _phoenix_frames() -> list[str]:
    frame1 = _build_sprite([
        "tttttrrrttttt",
        "ttttrooortttt",
        "tttrooooorttt",
        "tttoyyyotttt",
        "tttoywyyotttt",
        "tttoyyyottttt",
        "ttttoootttttt",
        "tttrrooorrttt",
        "ttrrottoorrt",
        "trottttttort",
        "trottttttort",
        "ttottttttott",
    ])
    frame2 = _build_sprite([
        "ttttrrrrtttt",
        "tttroooortt",
        "tttrooooortt",
        "tttoyyyotttt",
        "tttoywyyotttt",
        "tttoyyyottttt",
        "ttttoootttttt",
        "ttrrrooorrrtt",
        "trrrotttoorrrt",
        "rrottttttoorr",
        "trottttttortt",
        "ttottttttottt",
    ])
    return [frame1, frame2]


def _duck_frames() -> list[str]:
    frame1 = _build_sprite([
        "ttttyytttttt",
        "tttyyyyyyttt",
        "ttykyyyykytt",
        "ttyyyooyytt",
        "ttyyyyyyyytt",
        "tttyyyyytttt",
        "ttttyyyytttt",
        "tttyyyyytttt",
        "ttyyyyyyyytt",
        "tyyyyyyyyyt",
        "tttoottoottt",
        "tttoottoottt",
    ])
    frame2 = _build_sprite([
        "ttttyytttttt",
        "tttyyyyyyttt",
        "ttykyyyykytt",
        "ttyyyooyytt",
        "ttyyyyyyyytt",
        "tttyyyyytttt",
        "ttttyyyytttt",
        "tttyyyyytttt",
        "ttyyyyyyyytt",
        "tttyyyyyyttt",
        "ttttoottottt",
        "ttttoottottt",
    ])
    return [frame1, frame2]


def _cat_frames() -> list[str]:
    frame1 = _build_sprite([
        "teettttteett",
        "teeettteeet",
        "teeeeeeeeet",
        "tegeeeegeett",
        "teeeepeeeet",
        "teeeeeeeeett",
        "tteeeeeeett",
        "ttteeeeetttt",
        "ttteeeeettt",
        "ttteeeeettt",
        "ttteetteett",
        "ttteetteett",
    ])
    frame2 = _build_sprite([
        "teettttteett",
        "teeettteeet",
        "teeeeeeeeet",
        "teEeeeeEeett",
        "teeeepeeeet",
        "teeeeeeeeett",
        "tteeeeeeett",
        "ttteeeeetttt",
        "ttteeeeettee",
        "ttteeeeettet",
        "ttteetteett",
        "ttteetteett",
    ])
    return [frame1, frame2]


def _frog_frames() -> list[str]:
    frame1 = _build_sprite([
        "ttggtttggtt",
        "tgwgttgwgtt",
        "tggggggggtt",
        "tgkggggkgtt",
        "tggggggggtt",
        "tggrrrrggtt",
        "ttggggggtt",
        "tttggggtttt",
        "ttggttggttt",
        "tgggttgggt",
        "tgggtttggg",
        "tggttttggt",
    ])
    frame2 = _build_sprite([
        "ttggtttggtt",
        "tgggttgggt",
        "tggggggggtt",
        "tgEggggEgtt",
        "tggggggggtt",
        "tggrrrrggtt",
        "ttggggggtt",
        "tttggggtttt",
        "ttggtttggtt",
        "tgggtttgggt",
        "tgggtttggg",
        "ttgtttttgt",
    ])
    return [frame1, frame2]


def _hamster_frames() -> list[str]:
    frame1 = _build_sprite([
        "tttnnnnttttt",
        "ttnnnnnntttt",
        "tnnnnnnnnttt",
        "tnknnnnkntt",
        "tnnnnvnnntt",
        "tnnwnnwnnttt",
        "ttnnnnnntttt",
        "tttnnnntttt",
        "tttnnnnttttt",
        "tttnnnnttttt",
        "tttnntnnttt",
        "tttnntnnttt",
    ])
    frame2 = _build_sprite([
        "tttnnnnttttt",
        "ttnnnnnntttt",
        "tnnnnnnnnttt",
        "tnknnnnkntt",
        "tnnnnvnnntt",
        "tnnwnnwnnttt",
        "ttnnnnnntttt",
        "tttnnnntttt",
        "tttnnnnttttt",
        "ttttnnnnttt",
        "ttttnntnnttt",
        "ttttnntnnttt",
    ])
    return [frame1, frame2]


def _owl_frames() -> list[str]:
    frame1 = _build_sprite([
        "tttNNNNtttt",
        "ttNNNNNNttt",
        "tNNNNNNNNtt",
        "tNyNNNyNNtt",
        "tNykNNkyNtt",
        "tNNNoNNNNtt",
        "ttNNNNNNttt",
        "tttNNNNtttt",
        "ttNNNNNNttt",
        "tNNNNNNNNtt",
        "ttNNttNNttt",
        "ttNNttNNttt",
    ])
    frame2 = _build_sprite([
        "tttNNNNtttt",
        "ttNNNNNNttt",
        "tNNNNNNNNtt",
        "tNyNNNyNNtt",
        "tNyENNEyNtt",
        "tNNNoNNNNtt",
        "ttNNNNNNttt",
        "tttNNNNtttt",
        "ttNNNNNNttt",
        "tNNNNNNNNtt",
        "ttNNttNNttt",
        "ttNNttNNttt",
    ])
    return [frame1, frame2]


def _fox_frames() -> list[str]:
    frame1 = _build_sprite([
        "tootttttoott",
        "toootttooott",
        "tooooooooot",
        "towooooowot",
        "tokkooookot",
        "toooonoooot",
        "ttooowooott",
        "tttoooootttt",
        "tttooooottt",
        "tttoooootttt",
        "tttoottoott",
        "tttoottoott",
    ])
    frame2 = _build_sprite([
        "tootttttoott",
        "toootttooott",
        "tooooooooot",
        "towooooowot",
        "tokkooookot",
        "toooonoooot",
        "ttooowooott",
        "tttooooottttoo",
        "tttoooootttoot",
        "tttoooootttttt",
        "tttoottoott",
        "tttoottoott",
    ])
    return [frame1, frame2]


def _axolotl_frames() -> list[str]:
    frame1 = _build_sprite([
        "ppttttttpptt",
        "ppptttpppttt",
        "tppppppppttt",
        "tpkpppppkptt",
        "tpppppppptt",
        "tpppuuppptt",
        "ttppppppttt",
        "tttpppptttt",
        "tttppppttttt",
        "ttppttpptttt",
        "ttppttpptttt",
        "tppptttppptt",
    ])
    frame2 = _build_sprite([
        "ppttttttpptt",
        "ppptttpppttt",
        "tppppppppttt",
        "tpkpppppkptt",
        "tpppppppptt",
        "tpppooppptt",
        "ttppppppttt",
        "tttpppptttt",
        "tttppppttttt",
        "tttppttppttt",
        "tttppttpptt",
        "ttpptttpptt",
    ])
    return [frame1, frame2]


def _penguin_frames() -> list[str]:
    frame1 = _build_sprite([
        "ttttkktttttt",
        "tttkkkkttttt",
        "ttkkkkkkttt",
        "ttkwkkwkkttt",
        "ttkkokkktt",
        "ttwwwwwwttt",
        "ttwwwwwwttt",
        "tttwwwwtttt",
        "ttttwwtttttt",
        "ttttywytttt",
        "ttttyyttttt",
        "tttyytyyttt",
    ])
    frame2 = _build_sprite([
        "ttttkktttttt",
        "tttkkkkttttt",
        "ttkkkkkkttt",
        "ttkwkkwkkttt",
        "ttkkokkktt",
        "ttwwwwwwttt",
        "ttwwwwwwttt",
        "tttwwwwtttt",
        "ttttwwtttttt",
        "tttywywtttt",
        "ttttyyttttt",
        "tttyyttyytt",
    ])
    return [frame1, frame2]


def _dragon_frames() -> list[str]:
    frame1 = _build_sprite([
        "ttGGtttttttt",
        "tGGGGttttttt",
        "tGGGGGGttttt",
        "tGkGGGGGttt",
        "tGGGGGGGttt",
        "ttGGrGGtttt",
        "tttGGGGtttt",
        "ttGGGGGGttt",
        "tGGGttGGGtt",
        "tGGtttGGtt",
        "tGGttttGGtt",
        "tGGttttGGtt",
    ])
    frame2 = _build_sprite([
        "ttGGtttttttt",
        "tGGGGttttttt",
        "tGGGGGGttttt",
        "tGkGGGGGttt",
        "tGGGGGGGttt",
        "ttGGrGGtttrt",
        "tttGGGGttrtt",
        "ttGGGGGGttt",
        "tGGGttGGGtt",
        "tGGtttGGttt",
        "tGGttttGGtt",
        "tGGttttGGtt",
    ])
    return [frame1, frame2]


def _capybara_frames() -> list[str]:
    frame1 = _build_sprite([
        "tttNNNNNtttt",
        "ttNNNNNNNttt",
        "tNNNNNNNNNtt",
        "tNkNNNNkNNtt",
        "tNNNNNNNNtt",
        "tNNNnNNNNtt",
        "ttNNNNNNNttt",
        "tttNNNNNtttt",
        "ttNNNNNNNttt",
        "tNNNNNNNNNtt",
        "tNNNttNNNtt",
        "tNNNttNNNtt",
    ])
    frame2 = _build_sprite([
        "tttNNNNNtttt",
        "ttNNNNNNNttt",
        "tNNNNNNNNNtt",
        "tNENNNNENNtt",
        "tNNNNNNNNtt",
        "tNNNnNNNNtt",
        "ttNNNNNNNttt",
        "tttNNNNNtttt",
        "ttNNNNNNNttt",
        "tNNNNNNNNNtt",
        "tNNNttNNNtt",
        "tNNNttNNNtt",
    ])
    return [frame1, frame2]


def _mushroom_frames() -> list[str]:
    frame1 = _build_sprite([
        "tttrrrrttttt",
        "ttrrrrrrttt",
        "trrwrrwrrttt",
        "rrrrrrrrrttt",
        "rrwrrrwrrttt",
        "trrrrrrrtttt",
        "tttnnnntttt",
        "tttnnnntttt",
        "tttnnnntttt",
        "tttnnnntttt",
        "ttnnnnnntt",
        "ttnnnnnntt",
    ])
    frame2 = _build_sprite([
        "tttrrrrttttt",
        "ttrrrrrrttt",
        "trrwrrwrrttt",
        "rrrrrrrrrttt",
        "rrwrrrwrrttt",
        "trrrrrrrtttt",
        "tttnnnntttt",
        "tttnnnnttgtt",
        "tttnnnntttt",
        "tttnnnntttt",
        "ttnnnnnntt",
        "ttnnnnnntt",
    ])
    return [frame1, frame2]


def _kraken_frames() -> list[str]:
    frame1 = _build_sprite([
        "ttttPPPPtttt",
        "tttPPPPPPttt",
        "ttPPPPPPPPtt",
        "ttPwPPPwPPtt",
        "ttPkPPPkPPtt",
        "ttPPPPPPPPtt",
        "tttPPPPPPttt",
        "tPPtPPtPPttt",
        "PPttPPttPPtt",
        "PtttPPtttPtt",
        "PtttPPtttPtt",
        "ttttPPtttttt",
    ])
    frame2 = _build_sprite([
        "ttttPPPPtttt",
        "tttPPPPPPttt",
        "ttPPPPPPPPtt",
        "ttPwPPPwPPtt",
        "ttPkPPPkPPtt",
        "ttPPPPPPPPtt",
        "tttPPPPPPttt",
        "ttPtPPtPPttt",
        "tPttPPttPttt",
        "PtttPPtttPtt",
        "ttttPPtttPtt",
        "tttPPttPtttt",
    ])
    return [frame1, frame2]


def _unicorn_frames() -> list[str]:
    frame1 = _build_sprite([
        "ttttyytttttt",
        "ttttywtttttt",
        "ttttwwtttttt",
        "tttwwwwwtttt",
        "ttwwkwwwwttt",
        "ttwwwpwwwttt",
        "tttwwwwwtttt",
        "ttttwwwtttt",
        "tttwwwwwttt",
        "ttwwttwwttt",
        "ttwwtttwttt",
        "tpptttpptt",
    ])
    frame2 = _build_sprite([
        "ttttyytttttt",
        "ttttywtttttt",
        "ttttwwtttttt",
        "tttwwwwwtttt",
        "ttwwkwwwwttt",
        "ttwwwpwwwttt",
        "tttwwwwwtttt",
        "ttttwwwtttt",
        "tttwwwwwttt",
        "tttwwttwwttt",
        "tttwwtttwttt",
        "ttpptttpptt",
    ])
    return [frame1, frame2]


def _ghost_frames() -> list[str]:
    frame1 = _build_sprite([
        "ttttwwwwtttt",
        "tttwwwwwwttt",
        "ttwwwwwwwwtt",
        "ttwbwwwbwwtt",
        "ttwkwwwkwwtt",
        "ttwwwwwwwwtt",
        "ttwwweewwwtt",
        "ttwwwwwwwwtt",
        "ttwwwwwwwwtt",
        "ttwwwwwwwwtt",
        "twwttwwttwtt",
        "twtttwtttwtt",
    ])
    frame2 = _build_sprite([
        "ttttwwwwtttt",
        "tttwwwwwwttt",
        "ttwwwwwwwwtt",
        "ttwbwwwbwwtt",
        "ttwkwwwkwwtt",
        "ttwwwwwwwwtt",
        "ttwwweewwwtt",
        "ttwwwwwwwwtt",
        "ttwwwwwwwwtt",
        "ttwwwwwwwwtt",
        "ttwttwwttwttt",
        "ttwtttwttwttt",
    ])
    return [frame1, frame2]


def _cosmic_whale_frames() -> list[str]:
    frame1 = _build_sprite([
        "tttttBBBBBttt",
        "tttBBBBBBBBtt",
        "ttBBBBBBBBBBt",
        "tBBwBByBBwBBt",
        "tBBkBBBBBkBBt",
        "tBBBBBBBBBBBt",
        "ttBBBBBBBBBBt",
        "tttBBBBBBBBtt",
        "ttttBBBBBBttt",
        "tttttBBBBtttt",
        "ttytttBBttytt",
        "tttyttttytttt",
    ])
    frame2 = _build_sprite([
        "tttttBBBBBttt",
        "tttBBBBBBBBtt",
        "ttBBBBBBBBBBt",
        "tBBwBByBBwBBt",
        "tBBkBBBBBkBBt",
        "tBBBBBBBBBBBt",
        "ttBBBBBBBBBBt",
        "tttBBBBBBBBtt",
        "ttttBBBBBBttt",
        "tttttBBBBtttt",
        "tytttBBtttytt",
        "ttytttttytt",
    ])
    return [frame1, frame2]


# Build all sprite frames
SPRITES: dict[str, list[str]] = {
    "phoenix": _phoenix_frames(),
    "duck": _duck_frames(),
    "cat": _cat_frames(),
    "frog": _frog_frames(),
    "hamster": _hamster_frames(),
    "owl": _owl_frames(),
    "fox": _fox_frames(),
    "axolotl": _axolotl_frames(),
    "penguin": _penguin_frames(),
    "dragon": _dragon_frames(),
    "capybara": _capybara_frames(),
    "mushroom": _mushroom_frames(),
    "kraken": _kraken_frames(),
    "unicorn": _unicorn_frames(),
    "ghost": _ghost_frames(),
    "cosmic_whale": _cosmic_whale_frames(),
}

SHINY_BORDER = "[bold yellow]✨[/]"


def get_sprite(species_name: str, frame: int = 0, shiny: bool = False) -> str:
    """Get a sprite frame for a species."""
    frames = SPRITES.get(species_name, SPRITES["duck"])
    frame_idx = frame % len(frames)
    sprite = frames[frame_idx]
    if shiny:
        lines = sprite.split("\n")
        lines = [f"{SHINY_BORDER} {line} {SHINY_BORDER}" for line in lines]
        sprite = "\n".join(lines)
    return sprite


def get_frame_count(species_name: str) -> int:
    """Get number of animation frames for a species."""
    return len(SPRITES.get(species_name, SPRITES["duck"]))
