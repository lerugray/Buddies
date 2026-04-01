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
    # Frame 3: happy duck — eyes closed, beak open
    frame3 = _build_sprite([
        "ttttyytttttt",
        "tttyyyyyyttt",
        "ttyyyyyyyyytt",
        "ttyyyooyytt",
        "ttyyoooyytt",
        "tttyyyyytttt",
        "ttttyyyytttt",
        "tttyyyyytttt",
        "ttyyyyyyyytt",
        "tyyyyyyyyyt",
        "tttoottoottt",
        "tttoottoottt",
    ])
    # Frame 4: sleepy duck — half-closed eyes
    frame4 = _build_sprite([
        "ttttyytttttt",
        "tttyyyyyyttt",
        "ttyyyyyyyyytt",
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
    return [frame1, frame2, frame3, frame4]


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
    # Frame 3: cat loaf — tucked paws, content
    frame3 = _build_sprite([
        "teettttteett",
        "teeettteeet",
        "teeeeeeeeet",
        "teeeeeeeett",
        "teeeepeeeet",
        "teeeeeeeeett",
        "teeeeeeeeet",
        "teeeeeeeeet",
        "teeeeeeeeet",
        "teeeeeeeeet",
        "tteeeeeeett",
        "tttttttttttt",
    ])
    # Frame 4: curious cat — head tilted
    frame4 = _build_sprite([
        "ttteettteett",
        "tteeettteeet",
        "tteeeeeeeeet",
        "ttegeeeegeett",
        "tteeeepeeeet",
        "tteeeeeeeet",
        "ttteeeeeeett",
        "ttteeeeetttt",
        "ttteeeeettt",
        "ttteeeeettt",
        "ttteetteett",
        "ttteetteett",
    ])
    return [frame1, frame2, frame3, frame4]


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
        "tnnnnknnntt",
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
        "tnnnnknnntt",
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
        "tpppooppptt",
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
    # Frame 3: dragon fire breath — flame stream!
    frame3 = _build_sprite([
        "ttGGtttttttt",
        "tGGGGttttttt",
        "tGGGGGGttttt",
        "tGkGGGGGttt",
        "tGGGGGGGttt",
        "ttGGrGGrrrooo",
        "tttGGGGtrooot",
        "ttGGGGGGtrttt",
        "tGGGttGGGtt",
        "tGGtttGGtt",
        "tGGttttGGtt",
        "tGGttttGGtt",
    ])
    # Frame 4: dragon resting — wings folded, eyes half closed
    frame4 = _build_sprite([
        "ttGGtttttttt",
        "tGGGGttttttt",
        "tGGGGGGttttt",
        "tGEGGGGGttt",
        "tGGGGGGGttt",
        "ttGGGGGtttt",
        "tttGGGGtttt",
        "ttGGGGGGttt",
        "tGGGGGGGGtt",
        "tGGGGGGGGt",
        "ttGGttGGttt",
        "ttGGttGGttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # Frame 3: ghost fading — using gray instead of white
    frame3 = _build_sprite([
        "tttteeeetttt",
        "ttteeeeeeettt",
        "tteeeeeeeeett",
        "ttebebeeeebett",
        "ttekeeeeekeett",
        "tteeeeeeeeett",
        "tteeeeeeeeett",
        "tteeeeeeeeett",
        "tteeeeeeeeett",
        "tteeeeeeeeett",
        "teetteetteett",
        "tetttettteett",
    ])
    # Frame 4: ghost spooky face — mouth wide open
    frame4 = _build_sprite([
        "ttttwwwwtttt",
        "tttwwwwwwttt",
        "ttwwwwwwwwtt",
        "ttwbwwwbwwtt",
        "ttwkwwwkwwtt",
        "ttwwwwwwwwtt",
        "ttwwkkkwwwtt",
        "ttwwkkkwwwtt",
        "ttwwwwwwwwtt",
        "ttwwwwwwwwtt",
        "twwttwwttwtt",
        "twtttwtttwtt",
    ])
    return [frame1, frame2, frame3, frame4]


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


def _bee_frames() -> list[str]:
    """A busy little bee."""
    frame1 = _build_sprite([
        "ttttgggtttt",
        "ttggGGGgtt",
        "tgGGGGGGgtt",
        "tgGGYYGGgt",
        "tgGGGGGGgt",
        "ttgGGGGgt",
        "tttgggtt",
        "ttttttt",
    ])
    frame2 = _build_sprite([
        "ttgggggtttt",
        "tgGGGGGgt",
        "gGGGGGGGGt",
        "gGGYYGGGgt",
        "gGGGGGGGgt",
        "tgGGGGGgt",
        "ttggggt",
        "ttttttt",
    ])
    return [frame1, frame2]


def _slime_frames() -> list[str]:
    """A gelatinous slime."""
    frame1 = _build_sprite([
        "tttgggggtt",
        "ttggGGGggt",
        "tgGGGGGGgt",
        "gGGGGGGGGg",
        "gGGGGGGGGg",
        "gGGGGGGGGg",
        "ttggGGGggt",
        "ttttgggtt",
    ])
    return [frame1, frame1]  # Slime doesn't move much


def _raccoon_frames() -> list[str]:
    """A sneaky raccoon."""
    frame1 = _build_sprite([
        "tttttkkttt",
        "tttkkEEktt",
        "ttkEEEEEkt",
        "tkEkYYkEkt",
        "tEEEEEEEt",
        "tEERRRREt",
        "tEERRRRRt",
        "ttEEEEEt",
    ])
    return [frame1, frame1]


def _parrot_frames() -> list[str]:
    """A colorful parrot."""
    frame1 = _build_sprite([
        "tttttyyytt",
        "tttyyyRytt",
        "ttyRRRRRyt",
        "tyRkYkRRyt",
        "tRRRRRRRt",
        "tRRoooRt",
        "tRooRoRt",
        "tttRRRtt",
    ])
    return [frame1, frame1]


def _octopus_frames() -> list[str]:
    """An octopus with tentacles."""
    frame1 = _build_sprite([
        "ttttbbbtt",
        "tttBBBBt",
        "ttBBBBBBt",
        "tBBBkYkBt",
        "tBBBBBBBt",
        "tBtBtBtBt",
        "tBtBtBtBt",
        "tBtBtBtBt",
    ])
    return [frame1, frame1]


def _wolf_frames() -> list[str]:
    """A wolf."""
    frame1 = _build_sprite([
        "tttkkktt",
        "ttkEEEktt",
        "tkEEEEEkt",
        "kEkYYkEEk",
        "kEEEEEEk",
        "kEEEEEEk",
        "ttkkkktt",
        "tttttttt",
    ])
    return [frame1, frame1]


def _robot_frames() -> list[str]:
    """A robot."""
    frame1 = _build_sprite([
        "ttteeeett",
        "tteEEEEet",
        "teEEEEEet",
        "eEkYYkEEe",
        "eEEEEEEEe",
        "eEEwwEEEe",
        "teEEEEEet",
        "tteEEEEet",
    ])
    return [frame1, frame1]


def _tree_frames() -> list[str]:
    """A tree."""
    frame1 = _build_sprite([
        "ttttgytt",
        "tttgGygtt",
        "ttgGGGGgt",
        "tgGGGGGGt",
        "tGGGGGGGt",
        "ttttYYttt",
        "ttttYYttt",
        "ttttYYttt",
    ])
    return [frame1, frame1]


def _void_cat_frames() -> list[str]:
    """A cat from the void."""
    frame1 = _build_sprite([
        "tttEEEtt",
        "ttEEEEEtt",
        "tEEEEEEEt",
        "EEkYYkEEE",
        "EEEEEEEEt",
        "tEEEEEEEt",
        "ttEEEEEtt",
        "ttttttt",
    ])
    return [frame1, frame1]


# ============================================================
# HAT SPRITES — cosmetic accessories for buddies
# Each hat is 6 pixel rows (3 rendered lines) for compact fit
# ============================================================

def _hat_crown() -> str:
    """A classic crown with three golden peaks and black trim."""
    return _build_sprite([
        "tttyytyttytt",
        "ttyYYtYYYytt",
        "ttYYYYYYYYtt",
        "ttyYYYYYYytt",
        "ttkkkkkkkkt",
        "ttttttttttt",
    ])


def _hat_wizard() -> str:
    """A tall pointed wizard hat with a star accent."""
    return _build_sprite([
        "tttttBtttttt",
        "ttttBBBttttt",
        "tttBBBBBtttt",
        "ttBBBBBBBttt",
        "tBBBBBBBBBtt",
        "tttttytttttt",
    ])


def _hat_propeller() -> str:
    """A beanie with spinning propeller blades on top."""
    return _build_sprite([
        "tttrbrbrtt",
        "ttrrrrrrrtt",
        "ttrreeertt",
        "ttrrrrrrtt",
        "tttrrrrttt",
        "ttttttttt",
    ])


def _hat_tinyduck() -> str:
    """A tiny rubber duck perched as a hat."""
    return _build_sprite([
        "tttttoootttt",
        "ttttoooooott",
        "ttttooooottt",
        "ttttooootttt",
        "tttttttttttt",
        "tttttttttttt",
    ])


def _hat_tophat() -> str:
    """A tall formal top hat — unlocked at level 10."""
    return _build_sprite([
        "tttkkkkktttt",
        "tttkkkkktttt",
        "tttkkkkktttt",
        "tkkkkkkkkkt",
        "tkkkkkkkkkt",
        "ttttttttttt",
    ])


def _hat_halo() -> str:
    """A glowing golden halo — unlocked at 50+ patience."""
    return _build_sprite([
        "tttyyyyyyttt",
        "ttyttttttytt",
        "ttyttttttytt",
        "tttyyyyyyttt",
        "tttttttttttt",
        "tttttttttttt",
    ])


def _hat_horns() -> str:
    """Little red devil horns — unlocked at 50+ chaos."""
    return _build_sprite([
        "trttttttrtt",
        "trrttttrrtt",
        "ttrrttrrttt",
        "tttttttttttt",
        "tttttttttttt",
        "tttttttttttt",
    ])


def _hat_headphones() -> str:
    """Over-ear headphones — unlocked after 100 session events."""
    return _build_sprite([
        "ttteeeeeett",
        "ttettttttett",
        "tetttttttet",
        "tetttttttet",
        "tttttttttttt",
        "tttttttttttt",
    ])


def _hat_flower() -> str:
    """A pretty flower — found when ecstatic."""
    return _build_sprite([
        "tttttppttttt",
        "ttttppppttt",
        "tttppgpppttt",
        "ttttppppttt",
        "tttttGtttttt",
        "ttttttttttt",
    ])


def _hat_nightcap() -> str:
    """A droopy nightcap — earned through patience (boredom)."""
    return _build_sprite([
        "ttttttbbbbtt",
        "ttttbbbbbbbt",
        "tttbbbbwbttt",
        "ttbbbbbtttt",
        "ttttttttttt",
        "ttttttttttt",
    ])


# ============================================================
# PHASE 6 SPECIES
# ============================================================

def _dolphin_frames() -> list[str]:
    frame1 = _build_sprite([
        "ttttttttttttt",
        "tttteeeettttt",
        "ttteeeeeettt",
        "tteeeeeeeettt",
        "teeekeeeeett",
        "teeeeeeeeettt",
        "tteeeeeeeettt",
        "ttteeeeeettt",
        "tttteeeettttt",
        "tteeeeettttt",
        "tttteeeettttt",
        "ttttteettttt",
    ])
    frame2 = _build_sprite([
        "ttttttttttttt",
        "tttteeeettttt",
        "ttteeeeeettt",
        "tteeeeeeeettt",
        "teeekeeeeett",
        "teeeeeeeeettt",
        "tteeeeeeeettt",
        "ttteeeeeettt",
        "tttteeeettttt",
        "ttttteeeetttt",
        "tttteeeettttt",
        "ttteettttttt",
    ])
    return [frame1, frame2]


def _orca_frames() -> list[str]:
    frame1 = _build_sprite([
        "ttttttttttttt",
        "ttttkkkktttt",
        "tttkkkkkkttt",
        "ttkkkkkkkkttt",
        "tkwkkkkkkktt",
        "tkwwkkkkkkttt",
        "ttwwwkkkkkttt",
        "tttwwwkkktt",
        "ttttwwwkkttt",
        "ttwwwwwttttt",
        "tttttwwwttttt",
        "ttttttwwttttt",
    ])
    frame2 = _build_sprite([
        "ttttttttttttt",
        "ttttkkkktttt",
        "tttkkkkkkttt",
        "ttkkkkkkkkttt",
        "tkwkkkkkkktt",
        "tkwwkkkkkkttt",
        "ttwwwkkkkkttt",
        "tttwwwkkktt",
        "ttttwwwkkttt",
        "ttttwwwwwtttt",
        "tttwwwttttttt",
        "ttttwwttttttt",
    ])
    return [frame1, frame2]


def _chonk_frames() -> list[str]:
    # BIG round cat — the legendary chonk
    frame1 = _build_sprite([
        "ttootttootttt",
        "ttoooooootttt",
        "tooooooooottt",
        "tokooookoottt",
        "toooorkooott",
        "tooooooooott",
        "tooooooooottt",
        "tooooooooottt",
        "tooooooooottt",
        "tooooooooottt",
        "ttoottttoott",
        "ttoottttoott",
    ])
    frame2 = _build_sprite([
        "ttootttootttt",
        "ttoooooootttt",
        "tooooooooottt",
        "tokooookoottt",
        "tooookooott",
        "tooooooooott",
        "tooooooooottt",
        "tooooooooottt",
        "tooooooooottt",
        "tooooooooottt",
        "tttootttoott",
        "tttootttoott",
    ])
    # Frame 3: chonk sitting — maximum loaf
    frame3 = _build_sprite([
        "ttootttootttt",
        "ttoooooootttt",
        "tooooooooottt",
        "toooooookoottt",
        "tooookooott",
        "tooooooooott",
        "tooooooooottt",
        "tooooooooottt",
        "ooooooooooottt",
        "ooooooooooottt",
        "tttttttttttt",
        "tttttttttttt",
    ])
    # Frame 4: chonk yawn — mouth open wide
    frame4 = _build_sprite([
        "ttootttootttt",
        "ttoooooootttt",
        "tooooooooottt",
        "tokooookoottt",
        "tooorrrooott",
        "tooorrroooott",
        "tooooooooottt",
        "tooooooooottt",
        "tooooooooottt",
        "tooooooooottt",
        "ttoottttoott",
        "ttoottttoott",
    ])
    return [frame1, frame2, frame3, frame4]


def _panda_frames() -> list[str]:
    frame1 = _build_sprite([
        "ttkktttkktttt",
        "ttwwwwwwwtttt",
        "twwwwwwwwttt",
        "twkwwwwkwttt",
        "twkwwwwkwttt",
        "twwwkwwwwttt",
        "ttwwwwwwwtttt",
        "ttwwwwwwwttt",
        "twwwwwwwwttt",
        "twwwwwwwwttt",
        "ttwwttwwtttt",
        "ttwwttwwtttt",
    ])
    frame2 = _build_sprite([
        "ttkktttkktttt",
        "ttwwwwwwwtttt",
        "twwwwwwwwttt",
        "twkwwwwkwttt",
        "twkwwwwkwttt",
        "twwwkwwwwttt",
        "ttwwwwwwwtttt",
        "ttwwwwwwwttt",
        "twwwwwwwwttt",
        "twwwwwwwwttt",
        "tttwwtwwttttt",
        "tttwwtwwttttt",
    ])
    return [frame1, frame2]


def _starspawn_frames() -> list[str]:
    # Eldritch tentacle blob — Pac-Man ghost meets Cthulhu
    frame1 = _build_sprite([
        "ttttPPPPttttt",
        "tttPPPPPPtttt",
        "ttPPPPPPPPttt",
        "tPPwPPPPwPttt",
        "tPPPPPPPPPttt",
        "tPPPpppPPPttt",
        "ttPPPPPPPtttt",
        "ttPPPPPPPtttt",
        "tPPPPPPPPPttt",
        "tPtPPtPPtPttt",
        "tPttPttPtttt",
        "tttttttttttt",
    ])
    frame2 = _build_sprite([
        "ttttPPPPttttt",
        "tttPPPPPPtttt",
        "ttPPPPPPPPttt",
        "tPPwPPPPwPttt",
        "tPPPPPPPPPttt",
        "tPPPpppPPPttt",
        "ttPPPPPPPtttt",
        "ttPPPPPPPtttt",
        "tPPPPPPPPPttt",
        "ttPtPPtPttttt",
        "tttPttPttttt",
        "tttttttttttt",
    ])
    # Frame 3: tentacles spread wide — awakened
    frame3 = _build_sprite([
        "ttttPPPPttttt",
        "tttPPPPPPtttt",
        "ttPPPPPPPPttt",
        "tPPwPPPPwPttt",
        "tPPPPPPPPPttt",
        "tPPpppppPPttt",
        "ttPPPPPPPtttt",
        "tPPPPPPPPPttt",
        "PPtPPtPPtPPtt",
        "PtttPttPtttPt",
        "tttttttttttt",
        "tttttttttttt",
    ])
    # Frame 4: pulsing — smaller, then expand
    frame4 = _build_sprite([
        "ttttttttttttt",
        "ttttPPPPttttt",
        "tttPPPPPPtttt",
        "ttPPwPPwPPttt",
        "ttPPPPPPPPttt",
        "ttPPpppPPtttt",
        "tttPPPPPttttt",
        "tttPPPPPttttt",
        "ttPPPPPPPtttt",
        "tPtPPtPPtPttt",
        "tPttPttPtttt",
        "tttttttttttt",
    ])
    return [frame1, frame2, frame3, frame4]


def _basilisk_frames() -> list[str]:
    # Dark Souls curse frog — big googly eyes on top
    frame1 = _build_sprite([
        "twwttttwwtttt",
        "twkwttwkwtttt",
        "twwwttwwwtttt",
        "tttGGGGGttttt",
        "ttGGGGGGGtttt",
        "tGGGGGGGGGttt",
        "tGGGGGGGGGttt",
        "ttGGGGGGGtttt",
        "tttGGGGGttttt",
        "ttGGttGGttttt",
        "ttGGttGGttttt",
        "tGGGttGGGtttt",
    ])
    frame2 = _build_sprite([
        "twwttttwwtttt",
        "tkwwttwwktttt",
        "twwwttwwwtttt",
        "tttGGGGGttttt",
        "ttGGGGGGGtttt",
        "tGGGGGGGGGttt",
        "tGGGGGGGGGttt",
        "ttGGGGGGGtttt",
        "tttGGGGGttttt",
        "tttGGGGttttt",
        "ttGGttGGttttt",
        "tGGGttGGGtttt",
    ])
    return [frame1, frame2]


def _cane_toad_frames() -> list[str]:
    # Chunky toxic frog — bigger and meaner than regular frog
    frame1 = _build_sprite([
        "ttttttttttttt",
        "ttGGGGGGGtttt",
        "tGGGGGGGGGttt",
        "tGwGGGGGwGttt",
        "tGkGGGGGkGttt",
        "tGGGoooGGGttt",
        "tGGGGGGGGGttt",
        "ttGGGGGGGtttt",
        "tGGGGGGGGGttt",
        "tGGGGGGGGGttt",
        "ttGGtttGGtttt",
        "ttGGtttGGtttt",
    ])
    frame2 = _build_sprite([
        "ttttttttttttt",
        "ttGGGGGGGtttt",
        "tGGGGGGGGGttt",
        "tGwGGGGGwGttt",
        "tGkGGGGGkGttt",
        "tGGGoooGGGttt",
        "tGGGGGGGGGttt",
        "ttGGGGGGGtttt",
        "tGGGGGGGGGttt",
        "tGGGGGGGGGttt",
        "tttGGtGGttttt",
        "tttGGtGGttttt",
    ])
    return [frame1, frame2]


def _gorby_frames() -> list[str]:
    # Round pink blob — Kirby-like
    frame1 = _build_sprite([
        "ttttttttttttt",
        "ttttppppttttt",
        "tttpppppptttt",
        "ttppppppppttt",
        "tppkppppkpttt",
        "tppppppppptt",
        "tpppprrpppttt",
        "ttppppppppttt",
        "tttpppppptttt",
        "ttttppppttttt",
        "tttpptpptttt",
        "tttpptpptttt",
    ])
    frame2 = _build_sprite([
        "ttttttttttttt",
        "ttttppppttttt",
        "tttpppppptttt",
        "ttppppppppttt",
        "tppkppppkpttt",
        "tppppppppptt",
        "tpppprrpppttt",
        "ttppppppppttt",
        "tttpppppptttt",
        "ttttppppttttt",
        "ttttpppptttt",
        "tttpptpptttt",
    ])
    # Frame 3: gorby bounce — lifted up, no feet showing
    frame3 = _build_sprite([
        "ttttttttttttt",
        "ttttttttttttt",
        "ttttppppttttt",
        "tttpppppptttt",
        "ttppppppppttt",
        "tppkppppkpttt",
        "tppppppppptt",
        "tpppprrpppttt",
        "ttppppppppttt",
        "tttpppppptttt",
        "ttttppppttttt",
        "ttttttttttttt",
    ])
    # Frame 4: gorby inhale — puffed up wider
    frame4 = _build_sprite([
        "ttttttttttttt",
        "tttpppppptttt",
        "ttppppppppttt",
        "tppppppppppt",
        "ppkppppppkppt",
        "pppppppppppt",
        "ppppprppppptt",
        "tppppppppppt",
        "ttppppppppttt",
        "tttpppppptttt",
        "tttpptpptttt",
        "tttpptpptttt",
    ])
    return [frame1, frame2, frame3, frame4]


def _tardigrade_frames() -> list[str]:
    # Tiny indestructible water bear
    frame1 = _build_sprite([
        "ttttttttttttt",
        "ttttnnnnttttt",
        "tttnnnnnnttt",
        "ttnnnnnnnnttt",
        "tnknnnnnnkntt",
        "tnnnnnnnnntt",
        "ttnnnnnnnnttt",
        "nntnnnnnntnn",
        "nnttnnnnttnn",
        "tttnnttnntttt",
        "ttnnttttnntt",
        "ttnnttttnntt",
    ])
    frame2 = _build_sprite([
        "ttttttttttttt",
        "ttttnnnnttttt",
        "tttnnnnnnttt",
        "ttnnnnnnnnttt",
        "tnknnnnnnkntt",
        "tnnnnnnnnntt",
        "ttnnnnnnnnttt",
        "tntnnnnnntntt",
        "nnttnnnnttnnt",
        "tttnnttnntttt",
        "ttnnttttnnttt",
        "ttnnttttnnttt",
    ])
    return [frame1, frame2]


def _mantis_shrimp_frames() -> list[str]:
    # Colorful punching shrimp — uses multiple colors!
    frame1 = _build_sprite([
        "ttttttttttttt",
        "rrttrrrrttttt",
        "rrtooooortttt",
        "tttooooootttt",
        "ttkooookottt",
        "tttooooootttt",
        "tttyyyyyytttt",
        "tttggggggtttt",
        "ttttbbbbtttt",
        "tttttbbbttttt",
        "ttttttbbtttt",
        "tttttttbtttt",
    ])
    frame2 = _build_sprite([
        "ttttttttttttt",
        "ttrrrrrrttttt",
        "rrtooooorttt",
        "tttooooootttt",
        "ttkooookottt",
        "tttooooootttt",
        "tttyyyyyytttt",
        "tttggggggtttt",
        "ttttbbbbtttt",
        "tttttbbbttttt",
        "ttttttbbtttt",
        "tttttttbtttt",
    ])
    return [frame1, frame2]


# ============================================================
# FUN PHASE SPECIES
# ============================================================

def _corgi_frames() -> list[str]:
    """A round corgi with stubby legs."""
    frame1 = _build_sprite([
        "ttNNttNNttt",
        "tNNNNNNNNtt",
        "tNNNNNNNNtt",
        "NNkNNkNNNt",
        "NNNNNNNNNt",
        "NNNkkNNNNt",
        "tNNNNNNNNtt",
        "twwwwwwwwtt",
        "twwwwwwwwtt",
        "ttwwttwwttt",
        "ttwwttwwttt",
    ])
    frame2 = _build_sprite([
        "ttNNttNNttt",
        "tNNNNNNNNtt",
        "tNNNNNNNNtt",
        "NNkNNkNNNt",
        "NNNNNNNNNt",
        "NNNkkNNNNt",
        "tNNNNNNNNtt",
        "twwwwwwwwtt",
        "twwwwwwwwtt",
        "twwttttwwtt",
        "twwttttwwtt",
    ])
    return [frame1, frame2]


def _pig_frames() -> list[str]:
    """A round pink pig."""
    frame1 = _build_sprite([
        "tttppppttt",
        "ttpppppptt",
        "tpppppppt",
        "pkpppkpppt",
        "pppppppppt",
        "ppnnnppppt",
        "ppnkknpppt",
        "tpppppppt",
        "ttpppppptt",
        "ttpptppttt",
        "ttpptppttt",
    ])
    frame2 = _build_sprite([
        "tttppppttt",
        "ttpppppptt",
        "tpppppppt",
        "pkpppkpppt",
        "pppppppppt",
        "ppnnnppppt",
        "ppnkknpppt",
        "tpppppppt",
        "ttpppppptt",
        "ttptttptttt",
        "ttptttptttt",
    ])
    return [frame1, frame2]


def _doobie_frames() -> list[str]:
    """A weed leaf with a face. Chill vibes."""
    frame1 = _build_sprite([
        "tttttGttttt",
        "ttGttGttGtt",
        "tGGtGGtGGt",
        "tGGGGGGGGt",
        "GGGGGGGGGt",
        "GGkGGGkGGt",
        "GGGGGGGGGt",
        "GGGGwGGGGt",
        "tGGGGGGGtt",
        "ttttYYttttt",
        "ttttYYttttt",
        "ttttYYttttt",
    ])
    frame2 = _build_sprite([
        "tttttGttttt",
        "ttGttGttGtt",
        "tGGtGGtGGt",
        "tGGGGGGGGt",
        "GGGGGGGGGt",
        "GGGGGGGGt",
        "GGGGGGGGGt",
        "GGGwwwGGGt",
        "tGGGGGGGtt",
        "ttttYYttttt",
        "ttttYYttttt",
        "ttttYYttttt",
    ])
    return [frame1, frame2]


def _claude_frames() -> list[str]:
    """The Claude logo — a friendly little AI symbol."""
    frame1 = _build_sprite([
        "ttttoooottt",
        "tttoooooottt",
        "ttoooooooott",
        "tooooooooot",
        "oowooowoooo",
        "oooooooooot",
        "tooooooooot",
        "ttoowwwooott",
        "tttoooooott",
        "ttttooootttt",
    ])
    frame2 = _build_sprite([
        "ttttoooottt",
        "tttoooooottt",
        "ttoooooooott",
        "tooooooooot",
        "oowooowooot",
        "oooooooooot",
        "tooooooooot",
        "ttoowwwooott",
        "tttoooooott",
        "ttttooootttt",
    ])
    return [frame1, frame2]


def _illuminati_frames() -> list[str]:
    """An illuminati pyramid with a glowing eye."""
    frame1 = _build_sprite([
        "tttttytttttt",
        "ttttyYyttttt",
        "tttyYYYytttt",
        "tttYkwkYtttt",
        "ttYYYYYYyttt",
        "ttyYYYYYyttt",
        "tYYYYYYYYtt",
        "tyYYYYYYYYt",
        "YYYYYYYYYYt",
        "YYYYYYYYYYt",
    ])
    frame2 = _build_sprite([
        "tttttytttttt",
        "ttttyYyttttt",
        "tttyYYYytttt",
        "tttYwkwYtttt",
        "ttYYYYYYyttt",
        "ttyYYYYYyttt",
        "tYYYYYYYYtt",
        "tyYYYYYYYYt",
        "YYYYYYYYYYt",
        "YYYYYYYYYYt",
    ])
    return [frame1, frame2]


def _burger_frames() -> list[str]:
    """A cheeseburger with googly eyes."""
    frame1 = _build_sprite([
        "tttooooottt",
        "ttooooooott",
        "tooooooooot",
        "towotowoooo",
        "tooooooooot",
        "ggggggggggt",
        "yyyyyyyyyyy",
        "rrrrrrrrrrt",
        "NNNNNNNNNNt",
        "ttooooooott",
        "tttooooottt",
    ])
    frame2 = _build_sprite([
        "tttooooottt",
        "ttooooooott",
        "tooooooooot",
        "toowotowooo",
        "tooooooooot",
        "ggggggggggt",
        "yyyyyyyyyyy",
        "rrrrrrrrrrt",
        "NNNNNNNNNNt",
        "ttooooooott",
        "tttooooottt",
    ])
    return [frame1, frame2]


def _beholder_frames() -> list[str]:
    """A D&D beholder — big eye, eyestalks, floating."""
    frame1 = _build_sprite([
        "tgttgtttgtt",
        "gPtgPttgPtt",
        "tttttttttt",
        "tttPPPPtttt",
        "ttPPPPPPttt",
        "tPPPPPPPPtt",
        "PPwwwwPPPPt",
        "PwkwwkwPPPt",
        "PPwwwwPPPPt",
        "tPPPPPPPPtt",
        "ttPPPPPPttt",
        "tttPPPPtttt",
    ])
    frame2 = _build_sprite([
        "tttgtttgtgt",
        "ttgPttgPgPt",
        "tttttttttt",
        "tttPPPPtttt",
        "ttPPPPPPttt",
        "tPPPPPPPPtt",
        "PPwwwwPPPPt",
        "PwwkwkwPPPt",
        "PPwwwwPPPPt",
        "tPPPPPPPPtt",
        "ttPPPPPPttt",
        "tttPPPPtttt",
    ])
    return [frame1, frame2]


def _mimic_frames() -> list[str]:
    """A Dark Souls mimic chest — closed and then OPEN with tongue."""
    # Frame 1: looks like a normal chest
    frame1 = _build_sprite([
        "tYYYYYYYYYt",
        "YYYyYYyYYYt",
        "YYYYYYYYYYt",
        "YYYYkYYYYYt",
        "YYYYYYYYYYt",
        "NYYYYYYYYNt",
        "NYYYYYYYYNt",
        "NNNNNNNNNNt",
        "NNNNNNNNNNt",
        "ttNNttNNttt",
    ])
    # Frame 2: OPEN with teeth and tongue!
    frame2 = _build_sprite([
        "tYYYYYYYYYt",
        "YYYYYYYYYYt",
        "YwtwtwtwYYt",
        "YYYYYYYYYYt",
        "wrrrrrrrwt",
        "twrrrrrrwtt",
        "ttwrrrrwttt",
        "NNNNNNNNNNt",
        "NNNNNNNNNNt",
        "NttNttttNtt",
        "NttNttttNtt",
    ])
    return [frame1, frame2]


def _crab_frames() -> list[str]:
    """A little crab with clicky claws."""
    frame1 = _build_sprite([
        "rrttttttrrt",
        "rrrttttrrt",
        "trrrrrrrrtt",
        "trrrrrrrrtt",
        "rkrrrrrkrrt",
        "trrrrrrrrtt",
        "ttrrrrrrttt",
        "trrttttrrt",
        "rrttttttrrt",
    ])
    frame2 = _build_sprite([
        "trttttttrtt",
        "rrrttttrrt",
        "trrrrrrrrtt",
        "trrrrrrrrtt",
        "rkrrrrrkrrt",
        "trrrrrrrrtt",
        "ttrrrrrrttt",
        "trrttttrrtt",
        "rrttttttrrt",
    ])
    return [frame1, frame2]


def _moth_frames() -> list[str]:
    """A moth — attracted to the terminal glow."""
    frame1 = _build_sprite([
        "tttteetttt",
        "ttteeeeettt",
        "teeeeeeeett",
        "eeneeeneet",
        "eeeeeeeeett",
        "teeNNNeettt",
        "tttNNNttttt",
        "tttNNNttttt",
        "tteetteettt",
        "teettteett",
    ])
    frame2 = _build_sprite([
        "tttteetttt",
        "ttteeeeettt",
        "eeeeeeeeet",
        "eeneeeneeet",
        "eeeeeeeeet",
        "teeNNNeettt",
        "tttNNNttttt",
        "tttNNNttttt",
        "tteetteett",
        "teettteettt",
    ])
    return [frame1, frame2]


def _snail_frames() -> list[str]:
    """A snail with a spiral shell."""
    frame1 = _build_sprite([
        "tttNNNttttt",
        "ttNooNNtttt",
        "tNoooNNtttt",
        "tNNNNNNtttt",
        "ttNNNNNtttt",
        "yyyyyyyyyytt",
        "ykyyykyyyyt",
        "yyyyyyyyyyt",
        "tyyyyyyyytt",
    ])
    frame2 = _build_sprite([
        "tttNNNttttt",
        "ttNooNNtttt",
        "tNoooNNtttt",
        "tNNNNNNtttt",
        "ttNNNNNtttt",
        "tyyyyyyyyyytt",
        "tykyyykyyyyt",
        "tyyyyyyyyyyt",
        "ttyyyyyyyytt",
    ])
    return [frame1, frame2]


def _jellyfish_frames() -> list[str]:
    """A glowing jellyfish."""
    frame1 = _build_sprite([
        "tttcccctttt",
        "ttcccccctt",
        "tcccccccct",
        "tckccckccct",
        "tcccccccct",
        "ttcccccctt",
        "tctctctcttt",
        "tctctctcttt",
        "ttctctctttt",
        "tttctcttttt",
    ])
    frame2 = _build_sprite([
        "tttcccctttt",
        "ttcccccctt",
        "tcccccccct",
        "tckccckccct",
        "tcccccccct",
        "ttcccccctt",
        "ttctctctttt",
        "ttctctctttt",
        "tttctcttttt",
        "ttttctctttt",
    ])
    return [frame1, frame2]


def _sanic_frames() -> list[str]:
    """A blue hedgehog. Ironically not fast at all."""
    frame1 = _build_sprite([
        "tttttbbbttt",
        "ttttbbbbbtt",
        "tttbbbbbbbt",
        "ttbbbbbbbbt",
        "ttbbkbbkbbt",
        "ttbbnnnbbbt",
        "ttbbnnkbbbt",
        "tttbbbbbtt",
        "BBBtbbbtBBt",
        "tBBtbbbtBBt",
        "ttttbbtbbtt",
        "ttttbbbbtt",
    ])
    frame2 = _build_sprite([
        "tttttbbbttt",
        "ttttbbbbbtt",
        "tttbbbbbbbt",
        "ttbbbbbbbbt",
        "ttbkbbbkbbt",
        "ttbbnnnbbbt",
        "ttbbnknbbbt",
        "tttbbbbbtt",
        "BBBtbbbtBBt",
        "tBBtbbbtBt",
        "tttbbttbbtt",
        "tttbbttbbtt",
    ])
    return [frame1, frame2]


def _rat_frames() -> list[str]:
    """A sneaky little rat."""
    frame1 = _build_sprite([
        "teetteettt",
        "teeeeeettt",
        "teeeeeeet",
        "ekeeekeet",
        "teeeeeeet",
        "teeeneet",
        "tteeeeett",
        "ttteeeettt",
        "tteetteett",
        "tteetteett",
        "ttpttttptt",
    ])
    frame2 = _build_sprite([
        "teetteettt",
        "teeeeeettt",
        "teeeeeeet",
        "ekeeekeet",
        "teeeeeeet",
        "teeeneet",
        "tteeeeett",
        "ttteeeettt",
        "tteetteettt",
        "tteetteettt",
        "ttptttpttt",
    ])
    return [frame1, frame2]


def _rooster_frames() -> list[str]:
    """A proud rooster with a red comb."""
    frame1 = _build_sprite([
        "tttrrttttt",
        "ttrrrtttt",
        "ttrrNNtttt",
        "tNNNNNNttt",
        "NNkNNkNNtt",
        "NNNNNNNNtt",
        "NNoNNNNNtt",
        "tNNNNNNttt",
        "ttNNNNtttt",
        "gNNNNNNgtt",
        "gNNttNNgtt",
        "toottoott",
    ])
    frame2 = _build_sprite([
        "tttrrttttt",
        "ttrrrtttt",
        "ttrrNNtttt",
        "tNNNNNNttt",
        "NNkNNkNNtt",
        "NNNNNNNNtt",
        "NNoNNNNNtt",
        "tNNNNNNttt",
        "ttNNNNtttt",
        "gNNNNNNgtt",
        "ggNttNggtt",
        "tootttoott",
    ])
    return [frame1, frame2]


def _cow_frames() -> list[str]:
    """A spotted cow."""
    frame1 = _build_sprite([
        "ttwtttwtttt",
        "twwwwwwwttt",
        "twwwwwwwttt",
        "wkwEwkwwtt",
        "wwwwwwwwtt",
        "wwnnnwwwtt",
        "twwwwwwwttt",
        "ttEwwEwwttt",
        "tEwwwwEwttt",
        "twwwwwwwttt",
        "twwttwwttt",
        "twwttwwttt",
    ])
    frame2 = _build_sprite([
        "twttttwttt",
        "twwwwwwwttt",
        "twwwwwwwttt",
        "wkwEwkwwtt",
        "wwwwwwwwtt",
        "wwnnnwwwtt",
        "twwwwwwwttt",
        "ttEwwEwwttt",
        "tEwwwwEwttt",
        "twwwwwwwttt",
        "ttwwtwwttt",
        "ttwwtwwttt",
    ])
    return [frame1, frame2]


def _yog_sothoth_frames() -> list[str]:
    """Yog-Sothoth — a cluster of glowing spheres. The gate and the key."""
    frame1 = _build_sprite([
        "ttttPPtttt",
        "tttPPPPttt",
        "ttPPPPPttt",
        "tPpPPpPPtt",
        "PPPPPPPPPt",
        "PPpPPPpPtt",
        "tPPPPPPPPt",
        "PPPpPPPPPt",
        "PPPPPPpPPt",
        "tPPPPPPPtt",
        "ttPPPPPttt",
        "tttPPttttt",
    ])
    frame2 = _build_sprite([
        "tttPPttttt",
        "tttPPPPttt",
        "ttPPPPPPtt",
        "tPPpPPpPtt",
        "tPPPPPPPPt",
        "PPPPPpPPPt",
        "PPpPPPPPPt",
        "tPPPPpPPtt",
        "PPPpPPPPPt",
        "tPPPPPPPtt",
        "tttPPPtttt",
        "ttttPPtttt",
    ])
    return [frame1, frame2]


def _clippy_frames() -> list[str]:
    """A derpy paperclip with googly eyes. 'It looks like you're coding!'"""
    frame1 = _build_sprite([
        "ttteeeettt",
        "tteetteett",
        "teettteettt",
        "eettttteet",
        "eewtewteet",
        "eektektet",
        "eetttteet",
        "teewwweettt",
        "tteetteett",
        "teettteettt",
        "teettttttt",
        "tteeetttt",
    ])
    frame2 = _build_sprite([
        "ttteeeettt",
        "tteetteett",
        "teettteettt",
        "eettttteet",
        "eetwetweet",
        "eektetkeet",
        "eetttteet",
        "teewwweettt",
        "tteetteett",
        "teettteettt",
        "teettttttt",
        "tteeetttt",
    ])
    return [frame1, frame2]


def _goblin_frames() -> list[str]:
    """A green goblin with pointy ears and a toothy grin."""
    frame1 = _build_sprite([
        "tGGtttGGttt",
        "GGGGGGGGGtt",
        "tGGGGGGGGtt",
        "GGrGGGrGGtt",
        "tGGGGGGGGtt",
        "GGwGwGwGGtt",
        "tGGGGGGGGtt",
        "ttGGGGGGttt",
        "ttGGGGGGttt",
        "ttGGttGGttt",
        "ttGGttGGttt",
    ])
    frame2 = _build_sprite([
        "GGGtttGGGtt",
        "tGGGGGGGGtt",
        "tGGGGGGGGtt",
        "GGrGGGrGGtt",
        "tGGGGGGGGtt",
        "tGwGwGwGttt",
        "tGGGGGGGGtt",
        "ttGGGGGGttt",
        "ttGGGGGGttt",
        "tGGtttGGttt",
        "tGGtttGGttt",
    ])
    return [frame1, frame2]


def _imp_frames() -> list[str]:
    """A tiny red imp with horns and a pointed tail."""
    frame1 = _build_sprite([
        "trttttrtttt",
        "trrrrrrttt",
        "trrrrrrrttt",
        "rkrrrrrkrtt",
        "trrrrrrrttt",
        "trrwwrrrttt",
        "ttrrrrrtttt",
        "ttrrrrrttt",
        "ttrrttrrtt",
        "ttrrttrrtt",
        "tttttttrRtt",
        "tttttttRttt",
    ])
    frame2 = _build_sprite([
        "rtttttrttt",
        "trrrrrrttt",
        "trrrrrrrttt",
        "rkrrrrrkrtt",
        "trrrrrrrttt",
        "trwrrwrrttt",
        "ttrrrrrtttt",
        "ttrrrrrttt",
        "ttrrttrrttt",
        "ttrrttrrttt",
        "tRttttttttt",
        "ttRtttttttt",
    ])
    return [frame1, frame2]


def _kobold_frames() -> list[str]:
    """A small reptilian kobold with a snout."""
    frame1 = _build_sprite([
        "ttttoootttt",
        "ttoooooott",
        "toooooooott",
        "ooyoooyoott",
        "ooooooooott",
        "toooNNoottt",
        "ttooNNoott",
        "tttoooottt",
        "ttoooooott",
        "ttoottoottt",
        "ttoottoottt",
    ])
    frame2 = _build_sprite([
        "ttttoootttt",
        "ttoooooott",
        "toooooooott",
        "oyooooyoott",
        "ooooooooott",
        "toooNNoottt",
        "ttooNNoott",
        "tttoooottt",
        "ttoooooott",
        "ttoottoott",
        "ttoottoott",
    ])
    return [frame1, frame2]


def _joe_camel_frames() -> list[str]:
    """A cool camel with shades. Smooth operator."""
    frame1 = _build_sprite([
        "tttNNttttt",
        "ttNNNNtttt",
        "tNNNNNNttt",
        "NNkkkNNNtt",
        "NNkkkNNNtt",
        "tNNNNNtttt",
        "tNNNNNtttt",
        "ttNNNNtttt",
        "ttNNNNtttt",
        "tNNNNNNNtt",
        "NNNNNNNNNt",
        "NNtNNtNNtt",
        "NNtNNtNNtt",
    ])
    frame2 = _build_sprite([
        "tttNNttttt",
        "ttNNNNtttt",
        "tNNNNNNttt",
        "NNkkkNNNtt",
        "NNkkkNNNtt",
        "tNNNNNtttt",
        "tNNNNNtttt",
        "ttNNNNtttt",
        "ttNNNNtttt",
        "tNNNNNNNtt",
        "NNNNNNNNNt",
        "NNttNNttNNt",
        "NNttNNttNNt",
    ])
    return [frame1, frame2]


def _potato_frames() -> list[str]:
    """Just a potato. With a face. Running on potato hardware."""
    frame1 = _build_sprite([
        "tttNNNNtttt",
        "ttNNNNNNttt",
        "tNNNNNNNNtt",
        "NNkNNNkNNtt",
        "NNNNNNNNNtt",
        "NNNwwNNNNtt",
        "tNNNNNNNNtt",
        "ttNNNNNNttt",
        "tttNNNNtttt",
    ])
    frame2 = _build_sprite([
        "ttNNNNttttt",
        "tNNNNNNtttt",
        "NNNNNNNNttt",
        "NNkNNNkNNtt",
        "NNNNNNNNttt",
        "NNNNwwNNNtt",
        "tNNNNNNNNtt",
        "ttNNNNNNttt",
        "tttNNNNtttt",
    ])
    return [frame1, frame2]


def _bat_frames() -> list[str]:
    """A bat with spread wings."""
    frame1 = _build_sprite([
        "EEtttttttEEt",
        "EEEtttttEEEt",
        "EEEEtttEEEEt",
        "EEEEEEEEEEEt",
        "EEEkEEEkEEEt",
        "EEEEEEEEEEEt",
        "EEEEEwEEEEEt",
        "tEEEEEEEEEtt",
        "ttEEEEEEEttt",
        "tttEEtEEtttt",
    ])
    frame2 = _build_sprite([
        "tttttttttttt",
        "tEEtttttEEtt",
        "ttEEtttEEttt",
        "tttEEEEEtttt",
        "tttEEEEEtttt",
        "tttkEEEktttt",
        "tttEEEEEtttt",
        "tttEEwEEtttt",
        "ttttEEEttttt",
        "tttEEtEEtttt",
    ])
    return [frame1, frame2]


def _coffee_frames() -> list[str]:
    """A sentient coffee mug. Jittery."""
    frame1 = _build_sprite([
        "tteeeteettt",
        "tttetetettt",
        "tttetettttt",
        "twwwwwwwttt",
        "twNNNNNwtNt",
        "twNkNkNwtNt",
        "twNNNNNwtNt",
        "twNwwNNwtNt",
        "twNNNNNwttt",
        "twwwwwwwttt",
        "ttwwwwwtttt",
    ])
    frame2 = _build_sprite([
        "tteettttttt",
        "ttteteetttt",
        "tttetetettt",
        "twwwwwwwttt",
        "twNNNNNwtNt",
        "twkNNkNwtNt",
        "twNNNNNwtNt",
        "twNNwwNwtNt",
        "twNNNNNwttt",
        "twwwwwwwttt",
        "ttwwwwwtttt",
    ])
    return [frame1, frame2]


# Build hat sprites
HATS: dict[str, str] = {
    "crown": _hat_crown(),
    "wizard": _hat_wizard(),
    "propeller": _hat_propeller(),
    "tinyduck": _hat_tinyduck(),
    "tophat": _hat_tophat(),
    "halo": _hat_halo(),
    "horns": _hat_horns(),
    "headphones": _hat_headphones(),
    "flower": _hat_flower(),
    "nightcap": _hat_nightcap(),
}


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
    # Additional species
    "bee": _bee_frames(),
    "slime": _slime_frames(),
    "raccoon": _raccoon_frames(),
    "parrot": _parrot_frames(),
    "octopus": _octopus_frames(),
    "wolf": _wolf_frames(),
    "robot": _robot_frames(),
    "tree": _tree_frames(),
    "void_cat": _void_cat_frames(),
    # Phase 6 species
    "dolphin": _dolphin_frames(),
    "orca": _orca_frames(),
    "chonk": _chonk_frames(),
    "panda": _panda_frames(),
    "starspawn": _starspawn_frames(),
    "basilisk": _basilisk_frames(),
    "cane_toad": _cane_toad_frames(),
    "gorby": _gorby_frames(),
    "tardigrade": _tardigrade_frames(),
    "mantis_shrimp": _mantis_shrimp_frames(),
    # Fun phase species
    "corgi": _corgi_frames(),
    "pig": _pig_frames(),
    "doobie": _doobie_frames(),
    "claude": _claude_frames(),
    "illuminati": _illuminati_frames(),
    "burger": _burger_frames(),
    "beholder": _beholder_frames(),
    "mimic": _mimic_frames(),
    "crab": _crab_frames(),
    "moth": _moth_frames(),
    "snail": _snail_frames(),
    "jellyfish": _jellyfish_frames(),
    "sanic": _sanic_frames(),
    "rat": _rat_frames(),
    "rooster": _rooster_frames(),
    "cow": _cow_frames(),
    "yog_sothoth": _yog_sothoth_frames(),
    "clippy": _clippy_frames(),
    # Fun phase batch 2
    "goblin": _goblin_frames(),
    "imp": _imp_frames(),
    "kobold": _kobold_frames(),
    "joe_camel": _joe_camel_frames(),
    "potato": _potato_frames(),
    "bat": _bat_frames(),
    "coffee": _coffee_frames(),
}

SHINY_BORDER = "[bold yellow]✨[/]"


EVOLUTION_BORDERS = {
    "cyan": "[bold cyan]│[/]",
    "green": "[bold green]║[/]",
    "yellow": "[bold yellow]✦[/]",
}


def get_sprite(
    species_name: str,
    frame: int = 0,
    shiny: bool = False,
    hat: str | None = None,
    evolution_border: str | None = None,
) -> str:
    """Get a sprite frame for a species, with optional hat, shiny, and evolution border.

    Args:
        species_name: Name of the species
        frame: Animation frame index
        shiny: Whether to apply shiny border
        hat: Optional hat name to display above the sprite
        evolution_border: Color key for evolution stage border (cyan/green/yellow)

    Returns:
        Multi-line Rich markup string with the sprite
    """
    frames = SPRITES.get(species_name, SPRITES["duck"])
    frame_idx = frame % len(frames)
    sprite = frames[frame_idx]

    # Prepend hat if provided
    if hat and hat in HATS:
        sprite = HATS[hat] + "\n" + sprite

    # Apply evolution border (before shiny so both can stack)
    if evolution_border and evolution_border in EVOLUTION_BORDERS:
        border = EVOLUTION_BORDERS[evolution_border]
        lines = sprite.split("\n")
        lines = [f"{border} {line} {border}" for line in lines]
        sprite = "\n".join(lines)

    # Apply shiny border (outermost layer)
    if shiny:
        lines = sprite.split("\n")
        lines = [f"{SHINY_BORDER} {line} {SHINY_BORDER}" for line in lines]
        sprite = "\n".join(lines)

    return sprite


def get_frame_count(species_name: str) -> int:
    """Get number of animation frames for a species."""
    return len(SPRITES.get(species_name, SPRITES["duck"]))
