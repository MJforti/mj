"""Dev-only: subset the source fonts and write metrics.

Needs `pip install fonttools brotli`. The build itself (scripts/build.py) uses only the
standard library and reads the committed outputs:
  scripts/fonts/<name>.woff2   subset fonts, embedded into every SVG card
  scripts/fonts/metrics.json   advance widths, used to measure and wrap text
Run again only if you add characters that are not in CHARS.

Usage: python scripts/tools/subset_fonts.py <inter-dir> <jetbrains-mono-dir>
"""
import json, sys, pathlib
from fontTools import subset
from fontTools.ttLib import TTFont

CHARS = "".join(chr(c) for c in range(0x20, 0x7F)) + "·—–→←↗↘●○◉✓…×•▸’‘“”°₹▲▼█░"
OUT = pathlib.Path(__file__).resolve().parents[1] / "fonts"


def main(inter_dir, mono_dir):
    inter, mono = pathlib.Path(inter_dir), pathlib.Path(mono_dir)
    sources = {
        "display": inter / "InterDisplay-Bold.otf",
        "sans": inter / "Inter-Regular.otf",
        "sans-medium": inter / "Inter-Medium.otf",
        "sans-semibold": inter / "Inter-SemiBold.otf",
        "mono": mono / "jetbrains-mono-latin-400-normal.woff2",
        "mono-medium": mono / "jetbrains-mono-latin-500-normal.woff2",
    }
    metrics = {}
    for name, src in sources.items():
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern", "liga", "calt", "tnum"]
        opts.name_IDs = []
        opts.notdef_outline = True
        font = subset.load_font(str(src), opts)
        sub = subset.Subsetter(opts)
        sub.populate(text=CHARS)
        sub.subset(font)
        dst = OUT / f"{name}.woff2"
        subset.save_font(font, str(dst), opts)
        f = TTFont(str(src))
        cmap, hmtx = f.getBestCmap(), f["hmtx"]
        widths = {ch: hmtx[cmap[ord(ch)]][0] for ch in CHARS if ord(ch) in cmap}
        metrics[name] = {"upm": f["head"].unitsPerEm, "widths": widths}
        print(f"{name:14s} {dst.stat().st_size/1024:6.1f} KB  {len(widths)} glyphs")
    (OUT / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main(*sys.argv[1:3])
