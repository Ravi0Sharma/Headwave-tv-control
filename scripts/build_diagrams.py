"""Build documentation figures using Diagram Design's editorial SVG conventions.

HTML is the source artifact; SVG is extracted for GitHub README embedding.
Template/design attribution: docs/diagrams/THIRD_PARTY_LICENSE.txt.
No camera, model training, network requests, or TV access occurs here.
"""
import html
import re
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


def path(d):
    return f'<path d="{d}" fill="none" stroke="{MUTED}" stroke-width="1.2" marker-end="url(#arrow)"/>'


def edge_label(x, line_y, value):
    width = ((len(value)*6 + 16 + 3)//4)*4
    return (f'<rect x="{x-width/2}" y="{line_y-28}" width="{width}" height="20" fill="{PAPER}"/>'
            + text(x, line_y-14, value, 9, "Geist Mono", anchor="middle", color=MUTED))


def figure(slug, title, description, body, notes, kind="Architecture"):
    defs = ''.join(
        f'<marker id="{key}" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">'
        f'<polygon points="0 0, 8 3, 0 6" fill="{color}"/></marker>'
        for key, color in [("arrow", MUTED), ("arrow-accent", ACCENT), ("arrow-link", "#2e5aa8")])
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 600" '
           f'role="img" aria-labelledby="{slug}-title {slug}-desc">'
           f'<title id="{slug}-title">{html.escape(title)}</title>'
           f'<desc id="{slug}-desc">{html.escape(description)}</desc><defs>{defs}</defs>'
           f'<rect width="960" height="600" fill="{PAPER}"/>'
           + text(56, 48, f"HEADWAVE / {kind.upper()}", 8, "Geist Mono", color=MUTED)
           + text(56, 92, title, 28, "Instrument Serif")
           + text(56, 124, description, 12, color=MUTED)
           + body
           + f'<line x1="56" y1="536" x2="904" y2="536" stroke="#bfc0c0"/>'
           + text(56, 558, notes[0], 11, color=MUTED)
           + text(56, 580, notes[1], 11, color=MUTED)
           + '</svg>')
    doc = (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>{html.escape(title)} — Headwave</title>'
           f'<link href="{html.escape(FONT_URL, quote=True)}" rel="stylesheet">'
           '<style>*{box-sizing:border-box}body{margin:0;padding:24px;background:#f5f5f5;'
           'color:#2d3142;font-family:Geist,system-ui,sans-serif}main{max-width:1100px;margin:auto}'
           'svg{width:100%;height:auto;display:block}footer{font-size:12px;padding:16px 0;'
           'color:#4f5d75}a{color:#2e5aa8}@media print{body{padding:0}footer{display:none}}</style>'
           '</head><body><main>' + svg
           + '<footer>Headwave · Diagram Design · <a href="../../README.md">Project overview</a></footer>'
           '</main></body></html>')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{slug}.html").write_text(doc, encoding="utf-8")
    # Export the first SVG from the HTML, preserving accessible title/description.
    extracted = re.search(r"<svg\b.*?</svg>", doc, re.S).group(0)
    extracted = extracted.replace('<defs>', '<defs><style>@import url("'
                                   + html.escape(FONT_URL, quote=False) + '");</style>', 1)
    (OUT / f"{slug}.svg").write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + extracted, encoding="utf-8")


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
    body += text(56, 396, "Dry run: the same analysis runs, but intended commands are printed in the terminal.", 12)
    body += text(56, 424, "Camera Module 3 needs a Picamera2 adapter before OpenCV; this is not implemented yet.", 12)
    figure("pipeline", "From a hand gesture to a TV key", "Frames are processed locally. Recognizing a pose and choosing its TV key are separate decisions.", body,
           ["Orange highlights recognition. Arrows carry frame data and accepted commands.",
            "Mac for development · Raspberry Pi for operation · TV commands require --live"])

    body = row([
        ("Collect poses", "headwave collect", "MAC / SPACE KEY", False),
        ("Labeled points", "gestures.jsonl", "DATA / XYZ", False),
        ("Build model", "headwave train", "MAC / NORMALIZE", True),
        ("Test new poses", "--custom-model", "TEST / NEW SESSION", False),
        ("Copy to Pi", "custom.json", "DEPLOY / LATER", False),
    ])
    body += text(56, 396, "Training here prepares stored examples for comparison using five nearest neighbors.", 12)
    body += text(56, 424, "Choose gestures first. Collect intended poses and none. Add photos and measured results later.", 12)
    figure("training", "Custom hand poses: from samples to a model", "The workflow is prepared; personal training data and measured results will be added later.", body,
           ["Orange highlights model preparation. Arrows show how data and model files move.",
            "Collection stores no photos · MediaPipe's neural network is not retrained"])

    body = row([
        ("21 landmarks", "21 × (x, y, z)", "01 / INPUT", False),
        ("Wrist as origin", "p[i] − p[0]", "02 / RELATIVE", True),
        ("Normalize scale", "v / max(abs(v))", "03 / SCALE", False),
        ("63 feature values", "21 × 3 = 63", "04 / FEATURES", False),
    ], width=176, gap=48)
    body += text(56, 396, "Point 0 is the wrist. Fingertips are points 4, 8, 12, 16, and 20.", 12)
    body += text(56, 424, "Translation and scale matter less. Rotation and left/right hand differences are not removed.", 12)
    figure("preprocessing", "Preparing the hand landmarks", "features() describes hand shape using coordinates relative to the wrist.", body,
           ["Orange highlights the coordinate reference. Arrows show the preprocessing order.",
            "XYZ comes from the model; z is not a distance in meters. Personal hand photos will be added later."])

    body = (edge(272, 276, 380, 276) + edge_label(326, 276, "NEW POSE")
            + edge(580, 276, 688, 276) + edge_label(634, 276, "TIMING PASSED")
            + path("M 480,228 V 184 Q 480,176 472,176 H 180 Q 172,176 172,184 V 228")
            + edge_label(326, 176, "HOLD BROKEN")
            + path("M 788,324 V 392 Q 788,400 780,400 H 180 Q 172,400 172,392 V 324")
            + edge_label(480, 400, "RELEASE ≥0.35s")
            + node(72,228,"Ready", "waiting for pose",200,False,"01 / ARMED")
            + node(380,228,"Measure hold", "same pose ≥0.5 s",200,False,"02 / CANDIDATE")
            + node(688,228,"Fired and locked", "one command",200,True,"03 / LATCHED"))
    body += text(56, 456, "Score ≥0.75 is required. Firing also requires ≥1.0 s since the previous event.", 12)
    body += text(56, 484, "A changed candidate restarts the hold timer. Changing poses after firing does not unlock.", 12)
    figure("gesture-filter", "One command per held gesture", "The filter remembers earlier frames so a held hand cannot keep sending the same key.", body,
           ["Orange marks the latched state. Arrows show conditions for state changes.",
            "Release = no hand, an unmapped pose, or a low score. Brief dropouts do not rearm."], "State machine")

    body = ''.join(f'<line x1="{x}" y1="212" x2="{x}" y2="520" stroke="#bfc0c0" stroke-dasharray="3,3"/>' for x in (200,760))
    for y, label, returning in [(236,"PAIR :37123",False),(288,"PAIRED",True),
                                 (340,"CONNECT :40877",False),(392,"CONNECTED",True),
                                 (444,"KEYEVENT",False),(496,"RESPONSE",True)]:
        body += edge(760 if returning else 200, y, 200 if returning else 760, y, returning)
        body += edge_label(480, y, label)
    body += node(100,148,"Raspberry Pi", "same user account",200,True,"ADB",64)
    body += node(660,148,"Google TV", "Wireless debugging",200,False,"TV",64)
    figure("tv-connection", "Pair first. Connect next. Send a key.", "Pi and TV must reach each other on the local network. The Mac is not needed during operation.", body,
           ["Solid arrow = request · Dashed arrow = response · Orange = Pi initiates the connection.",
            "Ports are examples. Pairing requires a code; normal connection uses a different port."], "Sequence")


if __name__ == "__main__":
    main()
