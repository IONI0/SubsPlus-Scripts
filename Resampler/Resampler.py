# Resampler V1.2

import sys
import ass
import re

RESAMPLE_FACTOR = 1.5 # (720p to 1080p)

def change_resolution(doc):
    doc.info["PlayResX"] = "1920"
    doc.info["PlayResY"] = "1080"

def resample_styles(doc):
    for style in doc.styles:
        style.fontsize = round(style.fontsize * RESAMPLE_FACTOR, 0)
        if not (style.spacing == 0.1 or style.spacing == 0.01):
            style.spacing = round(style.spacing * RESAMPLE_FACTOR, 1)
        style.outline = round(style.outline * RESAMPLE_FACTOR, 1)
        style.shadow = round(style.shadow * RESAMPLE_FACTOR, 1)
        style.margin_l = round(style.margin_l * RESAMPLE_FACTOR, 0)
        style.margin_r = round(style.margin_r * RESAMPLE_FACTOR, 0)
        style.margin_v = round(style.margin_v * RESAMPLE_FACTOR, 0)


def resample_lines(doc):
    for event in doc.events:
        event.text = re.sub(r"\\fs([\d.]+)", lambda m: f"\\fs{round(float(m.group(1)) * RESAMPLE_FACTOR)}", event.text)
        event.text = re.sub(r"\\pos\(([\d.]+),([\d.]+)\)",
                            lambda m: f"\\pos({round(float(m.group(1)) * RESAMPLE_FACTOR)},{round(float(m.group(2)) * RESAMPLE_FACTOR)})",
                            event.text)


def main(inpath, outpath):
    with open(inpath, encoding='utf_8_sig') as f:
        doc = ass.parse(f)

    change_resolution(doc)
    resample_styles(doc)
    resample_lines(doc)

    with open(outpath, "w", encoding='utf_8_sig') as f:
        doc.dump_file(f)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"Usage: {sys.argv[0]} infile.ass outfile.ass")
    main(sys.argv[1], sys.argv[2])