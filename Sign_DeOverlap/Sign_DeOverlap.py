# Sign_DeOverlap V1.6

import re
import sys
from PIL import Image, ImageDraw, ImageFont

'''
- Uses logic based on an8 in style and an8 inline being different so run before style_cleanup.
- Also assumes an7 inline means normal and no inline an tag means an8. Change behaviour in make_caption_areas() if needed
- Assumes lines are sorted by start time
'''

scale = 1 # Change to 1.5 for 1080p
widen_ratio = 1.01 # Based on screen height
line_switching_threshold = 500 # Centiseconds threshold to send an2 lines sandwiched between 2 an8 lines to an8

script_width = int(1280 * scale)
script_height = int(720 * scale)

# No font so approximation
try:
    dialogue_font = ImageFont.load_default(50 * scale * 0.85)
except Exception:
    print("Make sure you have updated to >= 10.1.0", file=sys.stderr)
    sys.exit(1)
dialogue_spacing = 10 * scale

margin_v = 40 * scale

img = Image.new('RGB', (script_width, script_height), color='white')
draw = ImageDraw.Draw(img)

def line2dict(line):
    line_pattern = re.compile(r"(?P<Format>[^:]*): ?(?P<Layer>\d*), ?(?P<Start>[^,]*), ?(?P<End>[^,]*), ?(?P<Style>[^,]*), ?(?P<Name>[^,]*), ?(?P<MarginL>[^,]*), ?(?P<MarginR>[^,]*), ?(?P<MarginV>[^,]*), ?(?P<Effect>[^,]*),(?P<Text>.*\n)")
    match = line_pattern.match(line)
    if match:
        return {key: match.group(key) for key in line_pattern.groupindex}
    else:
        return None

def style2dict(line):
    line_pattern = re.compile(r"(?P<Format>[^:]*): ?(?P<Name>[^,]*), ?(?P<Fontname>[^,]*), ?(?P<Fontsize>[^,]*), ?(?P<PrimaryColour>[^,]*), ?(?P<SecondaryColour>[^,]*), ?(?P<OutlineColour>[^,]*), ?(?P<BackColour>[^,]*), ?(?P<Bold>[^,]*), ?(?P<Italic>[^,]*), ?(?P<Underline>[^,]*), ?(?P<StrikeOut>[^,]*), ?(?P<ScaleX>[^,]*), ?(?P<ScaleY>[^,]*), ?(?P<Spacing>[^,]*), ?(?P<Angle>[^,]*), ?(?P<BorderStyle>[^,]*), ?(?P<Outline>[^,]*), ?(?P<Shadow>[^,]*), ?(?P<Alignment>[^,]*), ?(?P<MarginL>[^,]*), ?(?P<MarginR>[^,]*), ?(?P<MarginV>[^,]*), ?(?P<Encoding>.*)\n")
    match = line_pattern.match(line)
    if match:
        return {key: match.group(key) for key in line_pattern.groupindex}
    else:
        return None

def dict2line(d):
    return "{Format}: {Layer},{Start},{End},{Style},{Name},{MarginL},{MarginR},{MarginV},{Effect},{Text}".format(**d)

def timestamp_to_centiseconds(timestamp):
    timestamp_split = timestamp.split(":")
    timestamp_sec_split = timestamp_split[2].split(".")
    hour = int(timestamp_split[0])
    minute = int(timestamp_split[1])
    second = int(timestamp_sec_split[0])
    centisecond = int(timestamp_sec_split[1])

    centiseconds = 360000*hour + 6000*minute + 100*second + centisecond
    return centiseconds

def centiseconds_to_timestamp(centiseconds):
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    seconds, centisecond = divmod(remainder, 100)

    timestamp = f"{hours:01d}:{minutes:02d}:{seconds:02d}.{centisecond:02d}"
    return timestamp

def convert_to_centiseconds(lines_list):
    for line_idx, line in enumerate(lines_list):
        if line.startswith("Dialogue: "):
            line_dict = line2dict(line)
            line_dict["Start"] = timestamp_to_centiseconds(line_dict["Start"])
            line_dict["End"] = timestamp_to_centiseconds(line_dict["End"])
            lines_list[line_idx] = dict2line(line_dict)

def convert_to_timestamp(lines_list):
    for line_idx, line in enumerate(lines_list):
        if line.startswith("Dialogue: "):
            line_dict = line2dict(line)
            line_dict["Start"] = centiseconds_to_timestamp(int(line_dict["Start"]))
            line_dict["End"] = centiseconds_to_timestamp(int(line_dict["End"]))
            lines_list[line_idx] = dict2line(line_dict)

def load_styles(lines_list):
    styles_dict = {}
    for line in lines_list:
        if line.startswith("Style: "):
            line_dict = style2dict(line)
            styles_dict[line_dict["Name"]] = line_dict

    return styles_dict

def widen_box(box, ratio):
    # Based on screen height
    ratio = ratio - 1
    pixels = script_height * ratio
    return (round(box[0] - pixels), round(box[1] - pixels), round(box[2] + pixels), round(box[3] + pixels))

def get_text_box_sign(text, font, xy):
    text_box = draw.textbbox(xy, text=text, font=font)
    out_box = widen_box((xy[0], xy[1], text_box[2], text_box[3]), widen_ratio)
    return out_box # (top_left x, top_left y, bottom right x, bottom right y)

def get_text_box_sign_an8(text, font, xy):
    text_box = draw.textbbox(xy, text=text, font=font, anchor="ma", align='center')
    out_box = widen_box((text_box[0], xy[1], text_box[2], text_box[3]), widen_ratio)
    return out_box # (top_left x, top_left y, bottom right x, bottom right y)

def get_text_box_dialogue(text):
    out_box = draw.textbbox((script_width/2, script_height - margin_v), text=text.replace("\\N", "\n"),
                             font=dialogue_font, anchor="md", align='center', spacing=dialogue_spacing)
    return widen_box(out_box, widen_ratio) # (top_left x, top_left y, bottom right x, bottom right y)

def get_text_box_dialogue_top(text, stack_size = 0):
    text = "\n" * stack_size + text
    out_box = draw.textbbox((script_width/2, margin_v), text=text.replace("\\N", "\n"),
                             font=dialogue_font, anchor="ma", align='center', spacing=dialogue_spacing)
    return widen_box(out_box, widen_ratio) # (top_left x, top_left y, bottom right x, bottom right y)

def time_overlap(line1, line2):
    return max(int(line1["Start"]), int(line2["Start"])) < min(int(line1["End"]), int(line2["End"]))

def pos_overlap(rect1, rect2):
    x1_tl, y1_tl, x1_br, y1_br = rect1
    x2_tl, y2_tl, x2_br, y2_br = rect2

    if x1_tl > x2_br or x2_tl > x1_br:
        return False

    if y1_tl > y2_br or y2_tl > y1_br:
        return False

    return True

def get_pos(text):
    pattern = re.compile(r'\\pos\((?P<xpos>[\d.]+),(?P<ypos>[\d.]+)\)')

    match = pattern.search(text)

    if match:
        xpos = float(match.group('xpos'))
        ypos = float(match.group('ypos'))
        return (xpos, ypos)
    else:
        return None

def make_caption_areas(lines_list, styles_dict):
    caption_list = []

    for line_idx, line in enumerate(lines_list):
        if not line.startswith("Dialogue: "):
            continue

        line_dict = line2dict(line)

        if "Caption" in line_dict["Style"]:
            pos = get_pos(line_dict["Text"])
            if not pos:
                # print(f"caption without pos: {line}")
                continue
            style = styles_dict[line_dict["Style"]]
            fontsize = int(style["Fontsize"])
            font = ImageFont.load_default(fontsize)
            text = line_dict["Text"].split("}")[-1].strip("\n")
            if "{\\an7}" in line_dict["Text"]:
                line_dict["Area"] = get_text_box_sign(text, font, pos)
            else:
                line_dict["Area"] = get_text_box_sign_an8(text, font, pos)
            # print(line_dict)
            caption_list.append(line_dict)

    return caption_list

def check_an8_spot(line_dict, an8_events, captions_list):
    # Do not go to an8 if there will be an overlap with a predefined an8 line
    for event in an8_events:
        if time_overlap(event, line_dict):
            return False

    # Check if overlaps with a sign when sent to an8
    # Doesn't check if stacking an8 lines overlap currently
    for caption_line in captions_list:
        if not time_overlap(line_dict, caption_line):
            continue

        text = line_dict["Text"].split("}")[-1].strip("\n")
        dialogue_box = get_text_box_dialogue_top(text)

        if pos_overlap(caption_line["Area"], dialogue_box):
            return False

    return True

def get_an8_events(lines_list, styles_dict):
    an8_events = []

    for line in lines_list:
        if line.startswith("Dialogue: "):
            line_dict = line2dict(line)
            if styles_dict[line_dict["Style"]]["Alignment"] == "8":
                an8_events.append(line_dict)

    return an8_events

def send_stacked_lines_to_top(lines_list, styles_dict, bottom_line, an8_events, captions_list):
    for line_idx, line in enumerate(lines_list):
        if not line.startswith("Dialogue: "):
            continue

        line_dict = line2dict(line)

        if "Subtitle" in line_dict["Style"] and styles_dict[line_dict["Style"]]["Alignment"] == "2":
            if time_overlap(line_dict, bottom_line):
                if not check_an8_spot(line_dict, an8_events, captions_list):
                    continue
                if "\\an8" not in line_dict["Text"]:
                    line_dict["Text"] = "{\\an8}" + line_dict["Text"]
                    lines_list[line_idx] = dict2line(line_dict)


def check_dialogue_overlap(lines_list, captions_list, styles_dict):
    an8_events = get_an8_events(lines_list, styles_dict)

    for line_idx, line in enumerate(lines_list):
        if not line.startswith("Dialogue: "):
            continue

        line_dict = line2dict(line)

        if "Subtitle" in line_dict["Style"] and styles_dict[line_dict["Style"]]["Alignment"] == "2":
            for caption_line in captions_list:
                if not time_overlap(line_dict, caption_line):
                    continue

                text = line_dict["Text"].split("}")[-1].strip("\n")
                dialogue_box = get_text_box_dialogue(text)

                if pos_overlap(caption_line["Area"], dialogue_box):
                    if not check_an8_spot(line_dict, an8_events, captions_list):
                        break
                    # Send stacked lines to an8
                    send_stacked_lines_to_top(lines_list, styles_dict, line_dict, an8_events, captions_list)
                    if "\\an8" not in line_dict["Text"]:
                        line_dict["Text"] = "{\\an8}" + line_dict["Text"]
                        lines_list[line_idx] = dict2line(line_dict)
                    break

def fix_line_switching(lines_list, captions_list, styles_dict):
    # Time based sending of lines to an8 if they are sandwiched between two an8 events that are within a timeframe
    an8_events = get_an8_events(lines_list, styles_dict)

    for line_idx, line in enumerate(lines_list):
        # First an8 line
        if not line.startswith("Dialogue: "):
            continue
        cur_line_dict = line2dict(lines_list[line_idx])
        if "\\an8" not in cur_line_dict["Text"]:
            continue
        cur_end_time = int(cur_line_dict["End"])

        # Look for next an8 within threshold
        lookahead = 1
        while True:
            try:
                next_line_dict = line2dict(lines_list[line_idx + lookahead])
                next_start_time = int(next_line_dict["Start"])
                if (next_start_time - cur_end_time) > line_switching_threshold:
                    break
                if "{\\an8}" not in next_line_dict["Text"]:
                    lookahead += 1
                    continue
                for i in range(line_idx + 1, line_idx + lookahead):
                    # Set in between lines to an8
                    line_dict = line2dict(lines_list[i])
                    if check_an8_spot(line_dict, an8_events, captions_list) and "\\an8" not in line_dict["Text"]:
                        line_dict["Text"] = "{\\an8}" + line_dict["Text"]
                        lines_list[i] = dict2line(line_dict)
                break
            except Exception:
                break

    # Inverse ducking sandwich. Insane edge case feel free to remove.

    counter = 0

    for line_idx, line in enumerate(lines_list):
        if not line.startswith("Dialogue: "):
            continue

        if counter < 2:
            counter += 1
            continue

        line_a = line2dict(lines_list[line_idx - 2])
        line_b = line2dict(lines_list[line_idx - 1])
        line_c = line2dict(lines_list[line_idx])

        if ("\\an8" not in line_a["Text"]) and ("\\an8" in line_b["Text"]) and ("\\an8" not in line_c["Text"]):
            for caption_line in captions_list:
                if not time_overlap(line_b, caption_line):
                    continue

                text_a = line_a["Text"].split("}")[-1].strip("\n")
                text_c = line_c["Text"].split("}")[-1].strip("\n")

                # If it would have not gone to an8 with the text box of the line before it, send it back to an2
                dialogue_box_a = get_text_box_dialogue_top(text_a)
                dialogue_box_c = get_text_box_dialogue_top(text_c)

                if pos_overlap(caption_line["Area"], dialogue_box_a) or pos_overlap(caption_line["Area"], dialogue_box_c):
                    line_b["Text"] = line_b["Text"].replace("{\\an8}", "")
                    lines_list[line_idx - 1] = dict2line(line_b)
                    break

def main(inpath, outpath):

    with open(inpath, encoding="utf-8") as infile:
        lines_list = infile.readlines()

    convert_to_centiseconds(lines_list)

    styles_dict = load_styles(lines_list)
    captions_list = make_caption_areas(lines_list, styles_dict)
    check_dialogue_overlap(lines_list, captions_list, styles_dict)
    fix_line_switching(lines_list, captions_list, styles_dict)

    convert_to_timestamp(lines_list)

    with open(outpath, "w", encoding="utf-8") as outfile:
        outfile.writelines(lines_list)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"Usage: {sys.argv[0]} infile.ass outfile.ass")

    main(sys.argv[1], sys.argv[2])
