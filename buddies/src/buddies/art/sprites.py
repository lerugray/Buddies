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
    # phoenix — happy (eyes squinted)
    frame3 = _build_sprite([
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
    # phoenix — sleepy (half-closed eyes)
    frame4 = _build_sprite([
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
    return [frame1, frame2, frame3, frame4]


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
    # frog — happy (eyes squinted)
    frame3 = _build_sprite([
        "ttggtttggtt",
        "tgwgttgwgtt",
        "tggggggggtt",
        "tggggggggtt",
        "tggggggggtt",
        "tggrrrrggtt",
        "ttggggggtt",
        "tttggggtttt",
        "ttggttggttt",
        "tgggttgggt",
        "tgggtttggg",
        "tggttttggt",
    ])
    # frog — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "ttggtttggtt",
        "tgwgttgwgtt",
        "tggggggggtt",
        "tgEggggEgtt",
        "tggggggggtt",
        "tggrrrrggtt",
        "ttggggggtt",
        "tttggggtttt",
        "ttggttggttt",
        "tgggttgggt",
        "tgggtttggg",
        "tggttttggt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # hamster — happy (eyes squinted)
    frame3 = _build_sprite([
        "tttnnnnttttt",
        "ttnnnnnntttt",
        "tnnnnnnnnttt",
        "tnnnnnnnntt",
        "tnnnnknnntt",
        "tnnwnnwnnttt",
        "ttnnnnnntttt",
        "tttnnnntttt",
        "tttnnnnttttt",
        "tttnnnnttttt",
        "tttnntnnttt",
        "tttnntnnttt",
    ])
    # hamster — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tttnnnnttttt",
        "ttnnnnnntttt",
        "tnnnnnnnnttt",
        "tnEnnnnEntt",
        "tnnnnknnntt",
        "tnnwnnwnnttt",
        "ttnnnnnntttt",
        "tttnnnntttt",
        "tttnnnnttttt",
        "tttnnnnttttt",
        "tttnntnnttt",
        "tttnntnnttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # owl — happy (eyes squinted)
    frame3 = _build_sprite([
        "tttNNNNtttt",
        "ttNNNNNNttt",
        "tNNNNNNNNtt",
        "tNyNNNyNNtt",
        "tNyNNNNyNtt",
        "tNNNoNNNNtt",
        "ttNNNNNNttt",
        "tttNNNNtttt",
        "ttNNNNNNttt",
        "tNNNNNNNNtt",
        "ttNNttNNttt",
        "ttNNttNNttt",
    ])
    # owl — sleepy (half-closed eyes)
    frame4 = _build_sprite([
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
    return [frame1, frame2, frame3, frame4]


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
    # fox — happy (eyes squinted)
    frame3 = _build_sprite([
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
    # fox — sleepy (half-closed eyes)
    frame4 = _build_sprite([
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
    return [frame1, frame2, frame3, frame4]


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
    # axolotl — happy (eyes squinted)
    frame3 = _build_sprite([
        "ppttttttpptt",
        "ppptttpppttt",
        "tppppppppttt",
        "tppppppppptt",
        "tpppppppptt",
        "tpppooppptt",
        "ttppppppttt",
        "tttpppptttt",
        "tttppppttttt",
        "ttppttpptttt",
        "ttppttpptttt",
        "tppptttppptt",
    ])
    # axolotl — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "ppttttttpptt",
        "ppptttpppttt",
        "tppppppppttt",
        "tpEpppppEptt",
        "tpppppppptt",
        "tpppooppptt",
        "ttppppppttt",
        "tttpppptttt",
        "tttppppttttt",
        "ttppttpptttt",
        "ttppttpptttt",
        "tppptttppptt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # penguin — happy (eyes squinted)
    frame3 = _build_sprite([
        "ttttyytttttt",
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
    # penguin — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "ttttEEtttttt",
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
    return [frame1, frame2, frame3, frame4]


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
    # capybara — happy (eyes squinted)
    frame3 = _build_sprite([
        "tttNNNNNtttt",
        "ttNNNNNNNttt",
        "tNNNNNNNNNtt",
        "tNNNNNNNNNtt",
        "tNNNNNNNNtt",
        "tNNNnNNNNtt",
        "ttNNNNNNNttt",
        "tttNNNNNtttt",
        "ttNNNNNNNttt",
        "tNNNNNNNNNtt",
        "tNNNttNNNtt",
        "tNNNttNNNtt",
    ])
    # capybara — sleepy (half-closed eyes)
    frame4 = _build_sprite([
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
    return [frame1, frame2, frame3, frame4]


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
    # mushroom — happy (eyes squinted)
    frame3 = _build_sprite([
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
    # mushroom — sleepy (half-closed eyes)
    frame4 = _build_sprite([
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
    return [frame1, frame2, frame3, frame4]


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
    # kraken — happy (eyes squinted)
    frame3 = _build_sprite([
        "ttttPPPPtttt",
        "tttPPPPPPttt",
        "ttPPPPPPPPtt",
        "ttPPPPPPPPtt",
        "ttPPPPPPPPtt",
        "ttPPPPPPPPtt",
        "tttPPPPPPttt",
        "tPPtPPtPPttt",
        "PPttPPttPPtt",
        "PtttPPtttPtt",
        "PtttPPtttPtt",
        "ttttPPtttttt",
    ])
    # kraken — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "ttttPPPPtttt",
        "tttPPPPPPttt",
        "ttPPPPPPPPtt",
        "ttPwPPPwPPtt",
        "ttPEPPPEPPtt",
        "ttPPPPPPPPtt",
        "tttPPPPPPttt",
        "tPPtPPtPPttt",
        "PPttPPttPPtt",
        "PtttPPtttPtt",
        "PtttPPtttPtt",
        "ttttPPtttttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # unicorn — happy (eyes squinted)
    frame3 = _build_sprite([
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
    # unicorn — sleepy (half-closed eyes)
    frame4 = _build_sprite([
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
    return [frame1, frame2, frame3, frame4]


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
    # cosmic_whale — happy (eyes squinted)
    frame3 = _build_sprite([
        "tttttBBBBBttt",
        "tttBBBBBBBBtt",
        "ttBBBBBBBBBBt",
        "tBBBBByBBBBBt",
        "tBBBBBBBBBBBt",
        "tBBBBBBBBBBBt",
        "ttBBBBBBBBBBt",
        "tttBBBBBBBBtt",
        "ttttBBBBBBttt",
        "tttttBBBBtttt",
        "ttytttBBttytt",
        "tttyttttytttt",
    ])
    # cosmic_whale — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tttttBBBBBttt",
        "tttBBBBBBBBtt",
        "ttBBBBBBBBBBt",
        "tBBwBByBBwBBt",
        "tBBEBBBBBEBBt",
        "tBBBBBBBBBBBt",
        "ttBBBBBBBBBBt",
        "tttBBBBBBBBtt",
        "ttttBBBBBBttt",
        "tttttBBBBtttt",
        "ttytttBBttytt",
        "tttyttttytttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # bee — happy (eyes squinted)
    frame3 = _build_sprite([
        "ttttgggtttt",
        "ttggGGGgtt",
        "tgGGGGGGgtt",
        "tgGGYYGGgt",
        "tgGGGGGGgt",
        "ttgGGGGgt",
        "tttgggtt",
        "ttttttt",
    ])
    # bee — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "ttttgggtttt",
        "ttggGGGgtt",
        "tgGGGGGGgtt",
        "tgGGYYGGgt",
        "tgGGGGGGgt",
        "ttgGGGGgt",
        "tttgggtt",
        "ttttttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # slime — happy (jiggles wider)
    frame3 = _build_sprite([
        "ttgggggggtt",
        "tggGGGGGggt",
        "gGGGGGGGGgt",
        "gGGGGGGGGGg",
        "gGGGGGGGGGg",
        "gGGGGGGGGGg",
        "tggGGGGGggt",
        "tttgggggtt",
    ])
    # slime — sleepy (flattens)
    frame4 = _build_sprite([
        "ttttttttttt",
        "ttggGGGggt",
        "tgGGGGGGgt",
        "gGGGGGGGGg",
        "gGGGGGGGGg",
        "gGGGGGGGGg",
        "tggGGGGggt",
        "ttgggggggtt",
    ])
    return [frame1, frame1, frame3, frame4]


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
    # raccoon — happy (eyes squinted)
    frame3 = _build_sprite([
        "tttttkkttt",
        "tttkkEEktt",
        "ttkEEEEEkt",
        "tkEEYYEEkt",
        "tEEEEEEEt",
        "tEERRRREt",
        "tEERRRRRt",
        "ttEEEEEt",
    ])
    # raccoon — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tttttkkttt",
        "tttkkEEktt",
        "ttkEEEEEkt",
        "tkEEYYEEkt",
        "tEEEEEEEt",
        "tEERRRREt",
        "tEERRRRRt",
        "ttEEEEEt",
    ])
    return [frame1, frame1, frame3, frame4]


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
    # parrot — happy (eyes squinted, beak open)
    frame3 = _build_sprite([
        "tttttyyytt",
        "tttyyyRytt",
        "ttyRRRRRyt",
        "tyRRYRRRyt",
        "tRRRRRRRt",
        "tRRoooRt",
        "tRooooRt",
        "tttRRRtt",
    ])
    # parrot — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tttttyyytt",
        "tttyyyRytt",
        "ttyRRRRRyt",
        "tyREYERRyt",
        "tRRRRRRRt",
        "tRRoooRt",
        "tRooRoRt",
        "tttRRRtt",
    ])
    return [frame1, frame1, frame3, frame4]


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
    # octopus — happy (eyes squinted, tentacles spread)
    frame3 = _build_sprite([
        "ttttbbbtt",
        "tttBBBBt",
        "ttBBBBBBt",
        "tBBBBYBBt",
        "tBBBBBBBt",
        "BtBtBtBtB",
        "BtBtBtBtB",
        "BtBtBtBtB",
    ])
    # octopus — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "ttttbbbtt",
        "tttBBBBt",
        "ttBBBBBBt",
        "tBBBEYEBt",
        "tBBBBBBBt",
        "tBtBtBtBt",
        "tBtBtBtBt",
        "ttBtBtBtt",
    ])
    return [frame1, frame1, frame3, frame4]


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
    # wolf — happy (eyes squinted)
    frame3 = _build_sprite([
        "tttkkktt",
        "ttkEEEktt",
        "tkEEEEEkt",
        "kEEYYEEEk",
        "kEEEEEEk",
        "kEEwEEEk",
        "ttkkkktt",
        "tttttttt",
    ])
    # wolf — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tttkkktt",
        "ttkEEEktt",
        "tkEEEEEkt",
        "kEeYYeEEk",
        "kEEEEEEk",
        "kEEEEEEk",
        "ttkkkktt",
        "tttttttt",
    ])
    return [frame1, frame1, frame3, frame4]


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
    # robot — happy (eyes as happy lights)
    frame3 = _build_sprite([
        "ttteeeett",
        "tteEEEEet",
        "teEEEEEet",
        "eEgYYgEEe",
        "eEEEEEEEe",
        "eEEwwEEEe",
        "teEEEEEet",
        "tteEEEEet",
    ])
    # robot — sleepy (dim eyes)
    frame4 = _build_sprite([
        "ttteeeett",
        "tteEEEEet",
        "teEEEEEet",
        "eEEYYEEEe",
        "eEEEEEEEe",
        "eEEEEEEEe",
        "teEEEEEet",
        "tteEEEEet",
    ])
    return [frame1, frame1, frame3, frame4]


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
    # tree — happy (leaves rustling, fruit appears)
    frame3 = _build_sprite([
        "tttggytt",
        "ttggGyggt",
        "tgGGGGGgt",
        "gGGrGGrGt",
        "tGGGGGGGt",
        "ttttYYttt",
        "ttttYYttt",
        "ttttYYttt",
    ])
    # tree — sleepy (leaves droop)
    frame4 = _build_sprite([
        "tttttttt",
        "tttgGytt",
        "ttgGGGgtt",
        "tgGGGGGGt",
        "tGGGGGGGt",
        "tGGGGGGGt",
        "ttttYYttt",
        "ttttYYttt",
    ])
    return [frame1, frame1, frame3, frame4]


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
    # void_cat — happy (eyes squinted, purring)
    frame3 = _build_sprite([
        "tttEEEtt",
        "ttEEEEEtt",
        "tEEEEEEEt",
        "EEEYYEEEE",
        "EEEpEEEEt",
        "tEEEEEEEt",
        "ttEEEEEtt",
        "ttttttt",
    ])
    # void_cat — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tttEEEtt",
        "ttEEEEEtt",
        "tEEEEEEEt",
        "EEeYYeEEE",
        "EEEEEEEEt",
        "tEEEEEEEt",
        "ttEEEEEtt",
        "ttttttt",
    ])
    return [frame1, frame1, frame3, frame4]


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
    # dolphin — happy (eyes squinted)
    frame3 = _build_sprite([
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
    # dolphin — sleepy (half-closed eyes)
    frame4 = _build_sprite([
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
    return [frame1, frame2, frame3, frame4]


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
    # orca — happy (eyes squinted)
    frame3 = _build_sprite([
        "ttttttttttttt",
        "ttttkkkktttt",
        "tttkkkkkkttt",
        "ttkkkkkkkkttt",
        "tkwkkkkkkktt",
        "tkwwkkkkkkttt",
        "ttwwwkkkkkttt",
        "ttteeekkktt",
        "tttteeeeettt",
        "ttwwwwwttttt",
        "tttttwwwttttt",
        "ttttttwwttttt",
    ])
    # orca — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "ttttttttttttt",
        "ttttkkkktttt",
        "tttkkkkkkttt",
        "ttkkkkkkkkttt",
        "tkwkkkkkkktt",
        "tkwwkkkkkkttt",
        "ttwwwkkkkkttt",
        "tttwwwkkktt",
        "ttttwwwEEttt",
        "ttwwwwwttttt",
        "tttttwwwttttt",
        "ttttttwwttttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # panda — happy (eyes squinted)
    frame3 = _build_sprite([
        "ttkktttkktttt",
        "ttwwwwwwwtttt",
        "teeeeeeeettt",
        "teeeeeeeettt",
        "teeeeeeeettt",
        "twwwkwwwwttt",
        "ttwwwwwwwtttt",
        "ttwwwwwwwttt",
        "twwwwwwwwttt",
        "twwwwwwwwttt",
        "ttwwttwwtttt",
        "ttwwttwwtttt",
    ])
    # panda — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "ttkktttkktttt",
        "ttwwwwwwwtttt",
        "twwwwwwwwttt",
        "twEwwwwEwttt",
        "twEwwwwEwttt",
        "twwwkwwwwttt",
        "ttwwwwwwwtttt",
        "ttwwwwwwwttt",
        "twwwwwwwwttt",
        "twwwwwwwwttt",
        "ttwwttwwtttt",
        "ttwwttwwtttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # basilisk — happy (eyes squinted)
    frame3 = _build_sprite([
        "tGGttttGGtttt",
        "tGGGttGGGtttt",
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
    # basilisk — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "twwttttwwtttt",
        "twEwttwEwtttt",
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
    return [frame1, frame2, frame3, frame4]


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
    # cane_toad — happy (eyes squinted)
    frame3 = _build_sprite([
        "ttttttttttttt",
        "ttGGGGGGGtttt",
        "tGGGGGGGGGttt",
        "tGGGGGGGGGttt",
        "tGGGGGGGGGttt",
        "tGGGoooGGGttt",
        "tGGGGGGGGGttt",
        "ttGGGGGGGtttt",
        "tGGGGGGGGGttt",
        "tGGGGGGGGGttt",
        "ttGGtttGGtttt",
        "ttGGtttGGtttt",
    ])
    # cane_toad — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "ttttttttttttt",
        "ttGGGGGGGtttt",
        "tGGGGGGGGGttt",
        "tGwGGGGGwGttt",
        "tGEGGGGGEGttt",
        "tGGGoooGGGttt",
        "tGGGGGGGGGttt",
        "ttGGGGGGGtttt",
        "tGGGGGGGGGttt",
        "tGGGGGGGGGttt",
        "ttGGtttGGtttt",
        "ttGGtttGGtttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # tardigrade — happy (eyes squinted)
    frame3 = _build_sprite([
        "ttttttttttttt",
        "ttttnnnnttttt",
        "tttnnnnnnttt",
        "ttnnnnnnnnttt",
        "tnnnnnnnnnntt",
        "tnnnnnnnnntt",
        "ttnnnnnnnnttt",
        "nntnnnnnntnn",
        "nnttnnnnttnn",
        "tttnnttnntttt",
        "ttnnttttnntt",
        "ttnnttttnntt",
    ])
    # tardigrade — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "ttttttttttttt",
        "ttttnnnnttttt",
        "tttnnnnnnttt",
        "ttnnnnnnnnttt",
        "tnEnnnnnnEntt",
        "tnnnnnnnnntt",
        "ttnnnnnnnnttt",
        "nntnnnnnntnn",
        "nnttnnnnttnn",
        "tttnnttnntttt",
        "ttnnttttnntt",
        "ttnnttttnntt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # mantis_shrimp — happy (eyes squinted)
    frame3 = _build_sprite([
        "ttttttttttttt",
        "rrttrrrrttttt",
        "rrtooooortttt",
        "tttooooootttt",
        "ttooooooottt",
        "tttooooootttt",
        "tttyyyyyytttt",
        "tttggggggtttt",
        "ttttbbbbtttt",
        "tttttbbbttttt",
        "ttttttbbtttt",
        "tttttttbtttt",
    ])
    # mantis_shrimp — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "ttttttttttttt",
        "rrttrrrrttttt",
        "rrtooooortttt",
        "tttooooootttt",
        "ttEooooEottt",
        "tttooooootttt",
        "tttyyyyyytttt",
        "tttggggggtttt",
        "ttttbbbbtttt",
        "tttttbbbttttt",
        "ttttttbbtttt",
        "tttttttbtttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # corgi — happy (eyes squinted)
    frame3 = _build_sprite([
        "ttNNttNNttt",
        "tNNNNNNNNtt",
        "tNNNNNNNNtt",
        "NNNNNNNNNt",
        "NNNNNNNNNt",
        "NNNNNNNNNt",
        "tNNNNNNNNtt",
        "twwwwwwwwtt",
        "twwwwwwwwtt",
        "ttwwttwwttt",
        "ttwwttwwttt",
    ])
    # corgi — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "ttNNttNNttt",
        "tNNNNNNNNtt",
        "tNNNNNNNNtt",
        "NNENNENNNt",
        "NNNNNNNNNt",
        "NNNEENNNNt",
        "tNNNNNNNNtt",
        "twwwwwwwwtt",
        "twwwwwwwwtt",
        "ttwwttwwttt",
        "ttwwttwwttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # pig — happy (eyes squinted)
    frame3 = _build_sprite([
        "tttppppttt",
        "ttpppppptt",
        "tpppppppt",
        "pppppppppt",
        "pppppppppt",
        "ppnnnppppt",
        "ppnppnpppt",
        "tpppppppt",
        "ttpppppptt",
        "ttpptppttt",
        "ttpptppttt",
    ])
    # pig — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tttppppttt",
        "ttpppppptt",
        "tpppppppt",
        "pEpppEpppt",
        "pppppppppt",
        "ppnnnppppt",
        "ppnEEnpppt",
        "tpppppppt",
        "ttpppppptt",
        "ttpptppttt",
        "ttpptppttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # doobie — happy (eyes squinted)
    frame3 = _build_sprite([
        "tttttGttttt",
        "ttGttGttGtt",
        "tGGtGGtGGt",
        "tGGGGGGGGt",
        "GGGGGGGGGt",
        "GGGGGGGGGt",
        "GGGGGGGGGt",
        "GGGGwGGGGt",
        "tGGGGGGGtt",
        "ttttYYttttt",
        "ttttYYttttt",
        "ttttYYttttt",
    ])
    # doobie — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tttttGttttt",
        "ttGttGttGtt",
        "tGGtGGtGGt",
        "tGGGGGGGGt",
        "GGGGGGGGGt",
        "GGEGGGEGGt",
        "GGGGGGGGGt",
        "GGGGwGGGGt",
        "tGGGGGGGtt",
        "ttttYYttttt",
        "ttttYYttttt",
        "ttttYYttttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # claude — happy (eyes squinted)
    frame3 = _build_sprite([
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
    # claude — sleepy (half-closed eyes)
    frame4 = _build_sprite([
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
    return [frame1, frame2, frame3, frame4]


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
    # illuminati — happy (eyes squinted)
    frame3 = _build_sprite([
        "tttttytttttt",
        "ttttyYyttttt",
        "tttyYYYytttt",
        "tttYYYYYtttt",
        "ttYYYYYYyttt",
        "ttyYYYYYyttt",
        "tYYYYYYYYtt",
        "tyYYYYYYYYt",
        "YYYYYYYYYYt",
        "YYYYYYYYYYt",
    ])
    # illuminati — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tttttytttttt",
        "ttttyYyttttt",
        "tttyYYYytttt",
        "tttYEwEYtttt",
        "ttYYYYYYyttt",
        "ttyYYYYYyttt",
        "tYYYYYYYYtt",
        "tyYYYYYYYYt",
        "YYYYYYYYYYt",
        "YYYYYYYYYYt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # burger — happy (eyes squinted)
    frame3 = _build_sprite([
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
    # burger — sleepy (half-closed eyes)
    frame4 = _build_sprite([
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
    return [frame1, frame2, frame3, frame4]


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
    # beholder — happy (eyes squinted)
    frame3 = _build_sprite([
        "tgttgtttgtt",
        "gPtgPttgPtt",
        "tttttttttt",
        "tttPPPPtttt",
        "ttPPPPPPttt",
        "tPPPPPPPPtt",
        "PPPPPPPPPPt",
        "PPPPPPPPPPt",
        "PPwwwwPPPPt",
        "tPPPPPPPPtt",
        "ttPPPPPPttt",
        "tttPPPPtttt",
    ])
    # beholder — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tgttgtttgtt",
        "gPtgPttgPtt",
        "tttttttttt",
        "tttPPPPtttt",
        "ttPPPPPPttt",
        "tPPPPPPPPtt",
        "PPwwwwPPPPt",
        "PwEwwEwPPPt",
        "PPwwwwPPPPt",
        "tPPPPPPPPtt",
        "ttPPPPPPttt",
        "tttPPPPtttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # mimic — happy (eyes squinted)
    frame3 = _build_sprite([
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
    # mimic — sleepy (half-closed eyes)
    frame4 = _build_sprite([
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
    return [frame1, frame2, frame3, frame4]


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
    # crab — happy (eyes squinted)
    frame3 = _build_sprite([
        "rrttttttrrt",
        "rrrttttrrt",
        "trrrrrrrrtt",
        "trrrrrrrrtt",
        "rrrrrrrrrrt",
        "trrrrrrrrtt",
        "ttrrrrrrttt",
        "trrttttrrt",
        "rrttttttrrt",
    ])
    # crab — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "rrttttttrrt",
        "rrrttttrrt",
        "trrrrrrrrtt",
        "trrrrrrrrtt",
        "rErrrrrErrt",
        "trrrrrrrrtt",
        "ttrrrrrrttt",
        "trrttttrrt",
        "rrttttttrrt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # moth — happy (eyes squinted)
    frame3 = _build_sprite([
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
    # moth — sleepy (half-closed eyes)
    frame4 = _build_sprite([
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
    return [frame1, frame2, frame3, frame4]


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
    # snail — happy (eyes squinted)
    frame3 = _build_sprite([
        "tttNNNttttt",
        "ttNooNNtttt",
        "tNoooNNtttt",
        "tNNNNNNtttt",
        "ttNNNNNtttt",
        "yyyyyyyyyytt",
        "yyyyyyyyyyt",
        "yyyyyyyyyyt",
        "tyyyyyyyytt",
    ])
    # snail — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tttNNNttttt",
        "ttNooNNtttt",
        "tNoooNNtttt",
        "tNNNNNNtttt",
        "ttNNNNNtttt",
        "yyyyyyyyyytt",
        "yEyyyEyyyyt",
        "yyyyyyyyyyt",
        "tyyyyyyyytt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # jellyfish — happy (eyes squinted)
    frame3 = _build_sprite([
        "tttcccctttt",
        "ttcccccctt",
        "tcccccccct",
        "tccccccccct",
        "tcccccccct",
        "ttcccccctt",
        "tctctctcttt",
        "tctctctcttt",
        "ttctctctttt",
        "tttctcttttt",
    ])
    # jellyfish — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tttcccctttt",
        "ttcccccctt",
        "tcccccccct",
        "tcEcccEccct",
        "tcccccccct",
        "ttcccccctt",
        "tctctctcttt",
        "tctctctcttt",
        "ttctctctttt",
        "tttctcttttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # sanic — happy (eyes squinted)
    frame3 = _build_sprite([
        "tttttbbbttt",
        "ttttbbbbbtt",
        "tttbbbbbbbt",
        "ttbbbbbbbbt",
        "ttbbbbbbbbt",
        "ttbbnnnbbbt",
        "ttbbnnkbbbt",
        "tttbbbbbtt",
        "BBBtbbbtBBt",
        "tBBtbbbtBBt",
        "ttttbbtbbtt",
        "ttttbbbbtt",
    ])
    # sanic — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tttttbbbttt",
        "ttttbbbbbtt",
        "tttbbbbbbbt",
        "ttbbbbbbbbt",
        "ttbbEbbEbbt",
        "ttbbnnnbbbt",
        "ttbbnnkbbbt",
        "tttbbbbbtt",
        "BBBtbbbtBBt",
        "tBBtbbbtBBt",
        "ttttbbtbbtt",
        "ttttbbbbtt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # rat — happy (eyes squinted)
    frame3 = _build_sprite([
        "teetteettt",
        "teeeeeettt",
        "teeeeeeet",
        "eeeeeeeet",
        "teeeeeeet",
        "teeeneet",
        "tteeeeett",
        "ttteeeettt",
        "tteetteett",
        "tteetteett",
        "ttpttttptt",
    ])
    # rat — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "teetteettt",
        "teeeeeettt",
        "teeeeeeet",
        "eEeeeEeet",
        "teeeeeeet",
        "teeeneet",
        "tteeeeett",
        "ttteeeettt",
        "tteetteett",
        "tteetteett",
        "ttpttttptt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # rooster — happy (eyes squinted)
    frame3 = _build_sprite([
        "tttrrttttt",
        "ttrrrtttt",
        "ttrrNNtttt",
        "tNNNNNNttt",
        "NNNNNNNNtt",
        "NNNNNNNNtt",
        "NNoNNNNNtt",
        "tNNNNNNttt",
        "ttNNNNtttt",
        "gNNNNNNgtt",
        "gNNttNNgtt",
        "toottoott",
    ])
    # rooster — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tttrrttttt",
        "ttrrrtttt",
        "ttrrNNtttt",
        "tNNNNNNttt",
        "NNENNENNtt",
        "NNNNNNNNtt",
        "NNoNNNNNtt",
        "tNNNNNNttt",
        "ttNNNNtttt",
        "gNNNNNNgtt",
        "gNNttNNgtt",
        "toottoott",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # cow — happy (eyes squinted)
    frame3 = _build_sprite([
        "ttwtttwtttt",
        "twwwwwwwttt",
        "tEEEEEEEttt",
        "EEEEEEEEtt",
        "wwwwwwwwtt",
        "wwnnnwwwtt",
        "twwwwwwwttt",
        "ttEwwEwwttt",
        "tEwwwwEwttt",
        "twwwwwwwttt",
        "twwttwwttt",
        "twwttwwttt",
    ])
    # cow — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "ttwtttwtttt",
        "twwwwwwwttt",
        "twwwwwwwttt",
        "wEwEwEwwtt",
        "wwwwwwwwtt",
        "wwnnnwwwtt",
        "twwwwwwwttt",
        "ttEwwEwwttt",
        "tEwwwwEwttt",
        "twwwwwwwttt",
        "twwttwwttt",
        "twwttwwttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # yog_sothoth — happy (eyes squinted)
    frame3 = _build_sprite([
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
    # yog_sothoth — sleepy (half-closed eyes)
    frame4 = _build_sprite([
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
    return [frame1, frame2, frame3, frame4]


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
    # clippy — happy (eyes squinted)
    frame3 = _build_sprite([
        "ttteeeettt",
        "tteetteett",
        "teettteettt",
        "eettttteet",
        "eeeteeteet",
        "eeeteetet",
        "eetttteet",
        "teewwweettt",
        "tteetteett",
        "teettteettt",
        "teettttttt",
        "tteeetttt",
    ])
    # clippy — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "ttteeeettt",
        "tteetteett",
        "teettteettt",
        "eettttteet",
        "eewtewteet",
        "eeEteEtet",
        "eetttteet",
        "teewwweettt",
        "tteetteett",
        "teettteettt",
        "teettttttt",
        "tteeetttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # goblin — happy (eyes squinted)
    frame3 = _build_sprite([
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
    # goblin — sleepy (half-closed eyes)
    frame4 = _build_sprite([
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
    return [frame1, frame2, frame3, frame4]


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
    # imp — happy (eyes squinted)
    frame3 = _build_sprite([
        "trttttrtttt",
        "trrrrrrttt",
        "trrrrrrrttt",
        "rrrrrrrrrtt",
        "trrrrrrrttt",
        "trrwwrrrttt",
        "ttrrrrrtttt",
        "ttrrrrrttt",
        "ttrrttrrtt",
        "ttrrttrrtt",
        "tttttttrRtt",
        "tttttttRttt",
    ])
    # imp — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "trttttrtttt",
        "trrrrrrttt",
        "trrrrrrrttt",
        "rErrrrrErtt",
        "trrrrrrrttt",
        "trrwwrrrttt",
        "ttrrrrrtttt",
        "ttrrrrrttt",
        "ttrrttrrtt",
        "ttrrttrrtt",
        "tttttttrRtt",
        "tttttttRttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # kobold — happy (eyes squinted)
    frame3 = _build_sprite([
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
    # kobold — sleepy (half-closed eyes)
    frame4 = _build_sprite([
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
    return [frame1, frame2, frame3, frame4]


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
    # joe_camel — happy (eyes squinted)
    frame3 = _build_sprite([
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
    # joe_camel — sleepy (half-closed eyes)
    frame4 = _build_sprite([
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
    return [frame1, frame2, frame3, frame4]


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
    # potato — happy (eyes squinted)
    frame3 = _build_sprite([
        "tttNNNNtttt",
        "ttNNNNNNttt",
        "tNNNNNNNNtt",
        "NNNNNNNNNtt",
        "NNNNNNNNNtt",
        "NNNwwNNNNtt",
        "tNNNNNNNNtt",
        "ttNNNNNNttt",
        "tttNNNNtttt",
    ])
    # potato — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tttNNNNtttt",
        "ttNNNNNNttt",
        "tNNNNNNNNtt",
        "NNENNNENNtt",
        "NNNNNNNNNtt",
        "NNNwwNNNNtt",
        "tNNNNNNNNtt",
        "ttNNNNNNttt",
        "tttNNNNtttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # bat — happy (eyes squinted)
    frame3 = _build_sprite([
        "EEtttttttEEt",
        "EEEtttttEEEt",
        "EEEEtttEEEEt",
        "EEEEEEEEEEEt",
        "EEEEEEEEEEEt",
        "EEEEEEEEEEEt",
        "EEEEEwEEEEEt",
        "tEEEEEEEEEtt",
        "ttEEEEEEEttt",
        "tttEEtEEtttt",
    ])
    # bat — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "EEtttttttEEt",
        "EEEtttttEEEt",
        "EEEEtttEEEEt",
        "EEEEEEEEEEEt",
        "EEEEEEEEEEEt",
        "EEEEEEEEEEEt",
        "EEEEEwEEEEEt",
        "tEEEEEEEEEtt",
        "ttEEEEEEEttt",
        "tttEEtEEtttt",
    ])
    return [frame1, frame2, frame3, frame4]


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
    # coffee — happy (eyes squinted)
    frame3 = _build_sprite([
        "tteeeteettt",
        "tttetetettt",
        "tttetettttt",
        "twwwwwwwttt",
        "tNNNNNNNtNt",
        "tNNNNNNNtNt",
        "twNNNNNwtNt",
        "twNwwNNwtNt",
        "twNNNNNwttt",
        "twwwwwwwttt",
        "ttwwwwwtttt",
    ])
    # coffee — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tteeeteettt",
        "tttetetettt",
        "tttetettttt",
        "twwwwwwwttt",
        "twNNNNNwtNt",
        "twNENENwtNt",
        "twNNNNNwtNt",
        "twNwwNNwtNt",
        "twNNNNNwttt",
        "twwwwwwwttt",
        "ttwwwwwtttt",
    ])
    return [frame1, frame2, frame3, frame4]


def _dali_clock_frames() -> list[str]:
    """A melting Salvador Dali clock. Time is subjective."""
    frame1 = _build_sprite([
        "tyyyyyyyyttt",
        "yYYYYYYYyttt",
        "yYkYYYkYyttt",
        "yYYYYYYYyttt",
        "yYYwwYYYyttt",
        "yYYYYYYYyttt",
        "tyyyyyyytttt",
        "tttttyyyyttt",
        "tttttttyyttt",
        "tttttttytttt",
        "ttttttytttt",
    ])
    frame2 = _build_sprite([
        "yyyyyyyyyttt",
        "yYYYYYYYyttt",
        "yYYkYkYYyttt",
        "yYYYYYYYyttt",
        "yYYwwYYYyttt",
        "yYYYYYYYyttt",
        "tyyyyyyyyytt",
        "ttttttyyyytt",
        "tttttttyyttt",
        "ttttttttyttt",
        "tttttttytttt",
    ])
    # dali_clock — happy (eyes squinted)
    frame3 = _build_sprite([
        "tyyyyyyyyttt",
        "yYYYYYYYyttt",
        "yYyYYYyYyttt",
        "yYYYYYYYyttt",
        "yYYwwYYYyttt",
        "yYYYYYYYyttt",
        "tyyyyyyytttt",
        "tttttyyyyttt",
        "tttttttyyttt",
        "tttttttytttt",
        "ttttttytttt",
    ])
    # dali_clock — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tyyyyyyyyttt",
        "yYYYYYYYyttt",
        "yYEYYYEYyttt",
        "yYYYYYYYyttt",
        "yYYwwYYYyttt",
        "yYYYYYYYyttt",
        "tyyyyyyytttt",
        "tttttyyyyttt",
        "tttttttyyttt",
        "tttttttytttt",
        "ttttttytttt",
    ])
    return [frame1, frame2, frame3, frame4]


def _comrade_frames() -> list[str]:
    """A hammer and sickle with googly eyes. Seizes the means of compilation."""
    frame1 = _build_sprite([
        "tttrrtttttt",
        "ttrrrrttttt",
        "tttrrttrrrt",
        "tttrrtrrRtt",
        "tttrrrrRttt",
        "tttwrrwttt",
        "tttrrRtttt",
        "ttrrRttttt",
        "trrRtttttt",
        "rrRttttttt",
    ])
    frame2 = _build_sprite([
        "ttttrrtttt",
        "tttrrrrttt",
        "ttttrrttrrrt",
        "ttttrrtrrRt",
        "ttttrrrrRtt",
        "ttttwrrwttt",
        "ttttrrRtttt",
        "tttrrRttttt",
        "ttrrRtttttt",
        "trrRttttttt",
    ])
    # comrade — happy (eyes squinted)
    frame3 = _build_sprite([
        "tttrrtttttt",
        "ttrrrrttttt",
        "tttrrttrrrt",
        "tttrrtrrRtt",
        "tttrrrrRttt",
        "tttwrrwttt",
        "tttrrRtttt",
        "ttrrRttttt",
        "trrRtttttt",
        "rrRttttttt",
    ])
    # comrade — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tttrrtttttt",
        "ttrrrrttttt",
        "tttrrttrrrt",
        "tttrrtrrRtt",
        "tttrrrrRttt",
        "tttwrrwttt",
        "tttrrRtttt",
        "ttrrRttttt",
        "trrRtttttt",
        "rrRttttttt",
    ])
    return [frame1, frame2, frame3, frame4]


def _box_frames() -> list[str]:
    """A cardboard box. ! Nothing to see here."""
    # Frame 1: just a box
    frame1 = _build_sprite([
        "ttttttttttt",
        "ttttttttttt",
        "NNNNNNNNNNN",
        "NNNNkNNNNNt",
        "NNNNNNNNNNN",
        "NNNNNNNNNNt",
        "NNNNNNNNNNt",
        "NNNNNNNNNNt",
        "NNNNNNNNNNt",
        "NNNNNNNNNNN",
    ])
    # Frame 2: eyes peeking out!
    frame2 = _build_sprite([
        "ttttttttttt",
        "tttwttwttt",
        "NNNkNNkNNNt",
        "NNNNNNNNNNt",
        "NNNNNNNNNNN",
        "NNNNNNNNNNt",
        "NNNNNNNNNNt",
        "NNNNNNNNNNt",
        "NNNNNNNNNNt",
        "NNNNNNNNNNN",
    ])
    # box — happy (eyes squinted)
    frame3 = _build_sprite([
        "ttttttttttt",
        "ttttttttttt",
        "NNNNNNNNNNN",
        "NNNNkNNNNNt",
        "NNNNNNNNNNN",
        "NNNNNNNNNNt",
        "NNNNNNNNNNt",
        "NNNNNNNNNNt",
        "NNNNNNNNNNt",
        "NNNNNNNNNNN",
    ])
    # box — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "ttttttttttt",
        "ttttttttttt",
        "NNNNNNNNNNN",
        "NNNNkNNNNNt",
        "NNNNNNNNNNN",
        "NNNNNNNNNNt",
        "NNNNNNNNNNt",
        "NNNNNNNNNNt",
        "NNNNNNNNNNt",
        "NNNNNNNNNNN",
    ])
    return [frame1, frame2, frame3, frame4]


def _bac_man_frames() -> list[str]:
    """A yellow circle that eats dots. Definitely not trademarked."""
    frame1 = _build_sprite([
        "tttyyyytttt",
        "ttyyyyyyttt",
        "tyyyyyyyyytt",
        "yyyyyyyyyyy",
        "yyyyyytttt",
        "yyyyyttttt",
        "yyyyyytttt",
        "yyyyyyyyyyy",
        "tyyyyyyyyytt",
        "ttyyyyyyttt",
        "tttyyyytttt",
    ])
    # Frame 2: mouth closed
    frame2 = _build_sprite([
        "tttyyyytttt",
        "ttyyyyyyttt",
        "tyyyyyyyyytt",
        "yyyyyyyyyyy",
        "yyyyyyyyyyy",
        "yyyyyyyyyyy",
        "yyyyyyyyyyy",
        "yyyyyyyyyyy",
        "tyyyyyyyyytt",
        "ttyyyyyyttt",
        "tttyyyytttt",
    ])
    # bac_man — happy (eyes squinted)
    frame3 = _build_sprite([
        "tttyyyytttt",
        "ttyyyyyyttt",
        "tyyyyyyyyytt",
        "yyyyyyyyyyy",
        "yyyyyytttt",
        "yyyyyttttt",
        "yyyyyytttt",
        "yyyyyyyyyyy",
        "tyyyyyyyyytt",
        "ttyyyyyyttt",
        "tttyyyytttt",
    ])
    # bac_man — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tttyyyytttt",
        "ttyyyyyyttt",
        "tyyyyyyyyytt",
        "yyyyyyyyyyy",
        "yyyyyytttt",
        "yyyyyttttt",
        "yyyyyytttt",
        "yyyyyyyyyyy",
        "tyyyyyyyyytt",
        "ttyyyyyyttt",
        "tttyyyytttt",
    ])
    return [frame1, frame2, frame3, frame4]


def _coopa_frames() -> list[str]:
    """A turtle troopa. Walks back and forth."""
    frame1 = _build_sprite([
        "ttttttttttt",
        "tttgggtttt",
        "ttgGGGGgttt",
        "tgGGGGGGttt",
        "tgGGGGGGttt",
        "ttgGGGgttt",
        "tttyyyyytt",
        "ttkyyyykttt",
        "ttyyyyytttt",
        "ttyyttyyttt",
        "ttyyttyyttt",
    ])
    frame2 = _build_sprite([
        "ttttttttttt",
        "tttgggtttt",
        "ttgGGGGgttt",
        "tgGGGGGGttt",
        "tgGGGGGGttt",
        "ttgGGGgttt",
        "tttyyyyytt",
        "ttkyyyykttt",
        "ttyyyyytttt",
        "tyytttyyttt",
        "tyytttyyttt",
    ])
    # coopa — happy (eyes squinted)
    frame3 = _build_sprite([
        "ttttttttttt",
        "tttgggtttt",
        "ttgGGGGgttt",
        "tgGGGGGGttt",
        "tgGGGGGGttt",
        "ttgGGGgttt",
        "tttyyyyytt",
        "ttyyyyyyttt",
        "ttyyyyytttt",
        "ttyyttyyttt",
        "ttyyttyyttt",
    ])
    # coopa — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "ttttttttttt",
        "tttgggtttt",
        "ttgGGGGgttt",
        "tgGGGGGGttt",
        "tgGGGGGGttt",
        "ttgGGGgttt",
        "tttyyyyytt",
        "ttEyyyyEttt",
        "ttyyyyytttt",
        "ttyyttyyttt",
        "ttyyttyyttt",
    ])
    return [frame1, frame2, frame3, frame4]


def _kilowatt_frames() -> list[str]:
    """A menacing lightbulb with a knife. Reddy Kilowatt's unhinged cousin."""
    frame1 = _build_sprite([
        "tttrrrttttt",
        "ttyyyyytttt",
        "tyyyyyyyttt",
        "tykyyyykttt",
        "tyyyyyyyttt",
        "tyywwyyttt",
        "ttyyyyytt",
        "tttyyytttt",
        "ttteyettttt",
        "tteeteettt",
        "tteetteett",
        "ttttttteett",
    ])
    frame2 = _build_sprite([
        "tttrrrttttt",
        "ttyyyyytttt",
        "tyyyyyyyttt",
        "tyykyykytt",
        "tyyyyyyyttt",
        "tywwwyyttt",
        "ttyyyyytt",
        "tttyyytttt",
        "ttteyettttt",
        "tteetteettt",
        "tteetteettt",
        "eettttttttt",
    ])
    # kilowatt — happy (eyes squinted)
    frame3 = _build_sprite([
        "tttrrrttttt",
        "ttyyyyytttt",
        "tyyyyyyyttt",
        "tyyyyyyyttt",
        "tyyyyyyyttt",
        "tyywwyyttt",
        "ttyyyyytt",
        "tttyyytttt",
        "ttteyettttt",
        "tteeteettt",
        "tteetteett",
        "ttttttteett",
    ])
    # kilowatt — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tttrrrttttt",
        "ttyyyyytttt",
        "tyyyyyyyttt",
        "tyEyyyyEttt",
        "tyyyyyyyttt",
        "tyywwyyttt",
        "ttyyyyytt",
        "tttyyytttt",
        "ttteyettttt",
        "tteeteettt",
        "tteetteett",
        "ttttttteett",
    ])
    return [frame1, frame2, frame3, frame4]


def _zorak_frames() -> list[str]:
    """Zorak — evil mantis from Space Ghost. Plays keyboard menacingly."""
    frame1 = _build_sprite([
        "tGGtttGGttt",
        "GGGGGGGGGtt",
        "GGrGGGrGGtt",
        "GGGGGGGGGtt",
        "GGGwwwGGGtt",
        "tGGGGGGGttt",
        "GtGGGGGtGtt",
        "GttGGGttGtt",
        "tttGGGttttt",
        "tttGtGttttt",
        "ttGGtGGtttt",
    ])
    frame2 = _build_sprite([
        "GGGtttGGGtt",
        "tGGGGGGGGtt",
        "GGrGGGrGGtt",
        "GGGGGGGGGtt",
        "GGwGwGwGGtt",
        "tGGGGGGGttt",
        "GtGGGGGtGtt",
        "GtGGGGGtGtt",
        "tttGGGttttt",
        "tttGtGttttt",
        "tttGtGttttt",
    ])
    # zorak — happy (eyes squinted)
    frame3 = _build_sprite([
        "tGGtttGGttt",
        "GGGGGGGGGtt",
        "GGrGGGrGGtt",
        "GGGGGGGGGtt",
        "GGGwwwGGGtt",
        "tGGGGGGGttt",
        "GtGGGGGtGtt",
        "GttGGGttGtt",
        "tttGGGttttt",
        "tttGtGttttt",
        "ttGGtGGtttt",
    ])
    # zorak — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "tGGtttGGttt",
        "GGGGGGGGGtt",
        "GGrGGGrGGtt",
        "GGGGGGGGGtt",
        "GGGwwwGGGtt",
        "tGGGGGGGttt",
        "GtGGGGGtGtt",
        "GttGGGttGtt",
        "tttGGGttttt",
        "tttGtGttttt",
        "ttGGtGGtttt",
    ])
    return [frame1, frame2, frame3, frame4]


def _anchor_frames() -> list[str]:
    """A nautical anchor. Keeps your code grounded."""
    frame1 = _build_sprite([
        "tttteetttt",
        "ttteeeettt",
        "tttteetttt",
        "tttteetttt",
        "ettteettte",
        "eetteetteet",
        "teeeeeeeet",
        "tteeeeeettt",
        "tttteetttt",
        "tttteetttt",
        "tttteettttt",
    ])
    # anchor — happy (glinting)
    frame3 = _build_sprite([
        "ttttwetttt",
        "ttteeeettt",
        "tttteetttt",
        "tttteetttt",
        "ettteettte",
        "eetteetteet",
        "teeeeeeeet",
        "tteeeeeettt",
        "tttteetttt",
        "tttteetttt",
        "tttteettttt",
    ])
    # anchor — sleepy (duller)
    frame4 = _build_sprite([
        "tttteetttt",
        "tttEEEEttt",
        "tttteetttt",
        "tttteetttt",
        "Ettteettte",
        "EEtteettEEt",
        "teeeeeeeet",
        "tteeeeeettt",
        "tttteetttt",
        "tttteetttt",
        "tttteettttt",
    ])
    return [frame1, frame1, frame3, frame4]


def _dice_frames() -> list[str]:
    """A rolling d6. RNG determines your fate."""
    frame1 = _build_sprite([
        "twwwwwwwttt",
        "wkwwwwkwttt",
        "wwwwwwwwttt",
        "wwwwkwwwttt",
        "wwwwwwwwttt",
        "wkwwwwkwttt",
        "twwwwwwwttt",
    ])
    frame2 = _build_sprite([
        "twwwwwwwttt",
        "wwwwwwwwttt",
        "wwkwwkwwttt",
        "wwwwwwwwttt",
        "wwkwwkwwttt",
        "wwwwwwwwttt",
        "twwwwwwwttt",
    ])
    # dice — happy (eyes squinted)
    frame3 = _build_sprite([
        "teeeeeeettt",
        "eeeeeeeettt",
        "wwwwwwwwttt",
        "wwwwkwwwttt",
        "wwwwwwwwttt",
        "eeeeeeeettt",
        "twwwwwwwttt",
    ])
    # dice — sleepy (half-closed eyes)
    frame4 = _build_sprite([
        "twwwwwwwttt",
        "wEwwwwEwttt",
        "wwwwwwwwttt",
        "wwwwkwwwttt",
        "wwwwwwwwttt",
        "wEwwwwEwttt",
        "twwwwwwwttt",
    ])
    return [frame1, frame2, frame3, frame4]


def _taco_frames() -> list[str]:
    """A taco. Holds everything together. Barely."""
    frame1 = _build_sprite([
        "tttooooottt",
        "ttoooooooott",
        "toggryrgott",
        "toggryrrgot",
        "toggryrgott",
        "ttoooooooott",
        "tttooooottt",
    ])
    frame2 = _build_sprite([
        "tttooooottt",
        "ttoooooooott",
        "torggyrgott",
        "torrgyrgot",
        "torggyrgott",
        "ttoooooooott",
        "tttooooottt",
    ])
    # taco — happy (fillings spilling out)
    frame3 = _build_sprite([
        "tttooooottt",
        "ttoooooooott",
        "toggryrgott",
        "toggryrrgot",
        "toggryrgotg",
        "ttoooooooott",
        "tttooooottt",
    ])
    # taco — sleepy (settled)
    frame4 = _build_sprite([
        "ttttttttttt",
        "tttooooottt",
        "ttoooooooott",
        "toggryrgott",
        "toggryrrgot",
        "ttoooooooott",
        "tttooooottt",
    ])
    return [frame1, frame2, frame3, frame4]


def _hat_safety_cone() -> str:
    """An orange traffic cone — unlocked via dominant snark."""
    return _build_sprite([
        "tttttootttttt",
        "ttttoooottttt",
        "tttOooooOtttt",
        "ttOOooooOOttt",
        "tOOOOOOOOOOt",
        "ttttttttttttt",
    ])


def _hat_apple() -> str:
    """A cute red apple with a green leaf — unlocked at level 15."""
    return _build_sprite([
        "ttttttggttttt",
        "tttttGggGtttt",
        "ttttrrrrrtttt",
        "ttttrrrrrttt",
        "tttttrrrtttt",
        "tttttttttttt",
    ])


def _hat_beanie() -> str:
    """A cozy knit beanie — unlocked via 50+ patience."""
    return _build_sprite([
        "tttttbbttttt",
        "tttbbbbbbtttt",
        "ttbBbBbBbBttt",
        "ttbbbbbbbbtt",
        "ttttttttttttt",
        "ttttttttttttt",
    ])


def _hat_antenna() -> str:
    """Alien antenna with a bouncy ball — found during exploring phase."""
    return _build_sprite([
        "tttttggttttt",
        "ttttteettttt",
        "ttttteettttt",
        "ttttteettttt",
        "ttttttttttttt",
        "ttttttttttttt",
    ])


def _hat_chef() -> str:
    """A tall white chef's toque — unlocked after 500+ messages."""
    return _build_sprite([
        "ttttwwwwwttt",
        "tttwwwwwwwtt",
        "tttwwwwwwwtt",
        "tttwwwwwwwtt",
        "ttkkkkkkkkt",
        "ttttttttttt",
    ])


def _hat_pirate() -> str:
    """A pirate tricorn — unlocked via dominant snark at level 10+."""
    return _build_sprite([
        "tttttwkttttt",
        "tttkkkkkktt",
        "ttkkkkkkkktt",
        "tkkkkkkkkkkt",
        "tteeeeeeett",
        "ttttttttttt",
    ])


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
    "safety_cone": _hat_safety_cone(),
    "apple": _hat_apple(),
    "beanie": _hat_beanie(),
    "antenna": _hat_antenna(),
    "chef": _hat_chef(),
    "pirate": _hat_pirate(),
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
    # Fun phase batch 3
    "dali_clock": _dali_clock_frames(),
    "comrade": _comrade_frames(),
    "box": _box_frames(),
    "bac_man": _bac_man_frames(),
    "coopa": _coopa_frames(),
    "kilowatt": _kilowatt_frames(),
    "zorak": _zorak_frames(),
    "anchor": _anchor_frames(),
    "dice": _dice_frames(),
    "taco": _taco_frames(),
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
