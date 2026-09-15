"""Build the SVG diagrams used in the README."""
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "diagrams"
PAPER, INK, MUTED, ACCENT = "#f5f5f5", "#2d3142", "#4f5d75", "#eb6c36"
FONT_URL = "https://fonts.googleapis.com/css2?family=Instrument+Serif&family=Geist:wght@400;500;600&family=Geist+Mono&display=swap"


def text(x, y, value, size=12, family="Geist", weight=400, anchor="start", color=INK):
    fallback = "monospace" if family == "Geist Mono" else "serif" if family == "Instrument Serif" else "sans-serif"
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-family="\'{family}\', {fallback}" '
            f'font-weight="{weight}" text-anchor="{anchor}" fill="{color}">{html.escape(value)}</text>')


def node(x, y, name, sub, width=144, focal=False, tag="", height=96):
    fill, stroke = ("#fbe9e0", ACCENT) if focal else ("#ffffff", INK)
    name_y, sub_y = (35, 54) if height == 64 else (49, 70)
    return (f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="6" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
            + text(x+12, y+20, tag, 8, "Geist Mono", color=MUTED)
            + text(x+width/2, y+name_y, name, 12, weight=600, anchor="middle")
            + text(x+width/2, y+sub_y, sub, 9, "Geist Mono", anchor="middle", color=MUTED))


def edge(x1, y1, x2, y2, dashed=False):
    assert x1 == x2 or y1 == y2, "Only axis-aligned straight connectors"
    dash = ' stroke-dasharray="5,4"' if dashed else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{MUTED}" '
            f'stroke-width="1.2" marker-end="url(#arrow)"{dash}/>')


def figure(slug, title, description, body, notes, kind="Architecture", height=600):
    defs = ''.join(
        f'<marker id="{key}" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">'
        f'<polygon points="0 0, 8 3, 0 6" fill="{color}"/></marker>'
        for key, color in [("arrow", MUTED), ("arrow-accent", ACCENT), ("arrow-link", "#2e5aa8")])
    note_block = (f'<line x1="56" y1="536" x2="904" y2="536" stroke="#bfc0c0"/>'
                  + text(56, 558, notes[0], 11, color=MUTED)
                  + text(56, 580, notes[1], 11, color=MUTED)) if notes else ""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {height}" '
           f'role="img" aria-labelledby="{slug}-title {slug}-desc">'
           f'<title id="{slug}-title">{html.escape(title)}</title>'
           f'<desc id="{slug}-desc">{html.escape(description)}</desc>'
           f'<defs><style>@import url("{html.escape(FONT_URL)}");</style>{defs}</defs>'
           f'<rect width="960" height="{height}" fill="{PAPER}"/>'
           + text(56, 48, f"HEADWAVE / {kind.upper()}", 8, "Geist Mono", color=MUTED)
           + text(56, 92, title, 28, "Instrument Serif")
           + text(56, 124, description, 12, color=MUTED)
           + body
           + note_block
           + '</svg>')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{slug}.svg").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n' + svg,
        encoding="utf-8",
    )


def row(items, y=228, width=144, gap=32):
    start = (960 - len(items)*width - (len(items)-1)*gap)/2
    xs = [start+i*(width+gap) for i in range(len(items))]
    result = ''.join(edge(xs[i]+width, y+48, xs[i+1], y+48) for i in range(len(items)-1))
    result += ''.join(node(x, y, name, sub, width, focal, tag) for x, (name, sub, tag, focal) in zip(xs, items))
    return result


def main():
    body = row([
        ("Camera + OpenCV", "frame / BGR → RGB", "01 / CAPTURE", False),
        ("MediaPipe", "21 points + pose", "02 / RECOGNIZE", True),
        ("Gesture filter", "score + hold time", "03 / ACCEPT", False),
        ("Choose TV key", "config.gestures", "04 / MAP", False),
        ("ADB → Google TV", "input keyevent", "05 / LIVE", False),
    ])
    figure("pipeline", "From a hand gesture to a TV key", "Frames are processed locally. Recognizing a pose and choosing its TV key are separate decisions.", body,
           [], height=360)

    body = row([
        ("Collect poses", "headwave collect", "01 / COLLECT", False),
        ("Labeled points", "gestures.jsonl", "02 / DATA", False),
        ("Build model", "headwave train", "03 / TRAIN", True),
        ("Test new poses", "--custom-model", "04 / TEST", False),
        ("Copy to Pi", "custom.json", "05 / DEPLOY", False),
    ])
    figure(
        "training",
        "Train custom hand gestures",
        "Collect labeled landmarks, create a model, test it, and copy it to Raspberry Pi.",
        body,
        [],
        height=360,
    )


if __name__ == "__main__":
    main()
