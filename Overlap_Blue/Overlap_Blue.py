# Overlap_Blue V2.3
import sys
import re

DIALOGUE_FONT = "SPOverrideF" # Set to None to be any font
COLOR_HEX = "&H743E15&"
CENTISECOND_LENIENCY = 3 # Don't count as overlap if it is less than _ centiseconds

def line2dict(line):
    line_pattern = re.compile(r"(?P<Format>[^:]*): ?(?P<Layer>\d*), ?(?P<Start>[^,]*), ?(?P<End>[^,]*), ?(?P<Style>[^,]*), ?(?P<Name>[^,]*), ?(?P<MarginL>[^,]*), ?(?P<MarginR>[^,]*), ?(?P<MarginV>[^,]*), ?(?P<Effect>[^,]*),(?P<Text>.*\n)")
    """pull fields out of ass event into dictionary
    takes string line as argument and returns dictionary or None if line is not an ASS event"""
    # print(line) # <- fun UnicodeEncodeErrors!
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

def generate_styles_list(lines_list):
    is_valid_style_bottom = []
    is_valid_style_top = []

    for line in lines_list:
        if line.startswith("Style: "):
            style_split = line.split(",")
            style_name = style_split[0].replace("Style: ", "")
            style_font = style_split[1]
            style_align = style_split[18]
            if (style_font == DIALOGUE_FONT or DIALOGUE_FONT == None) and style_align == "2":
                is_valid_style_bottom.append(style_name)
            elif (style_font == DIALOGUE_FONT or DIALOGUE_FONT == None) and style_align == "8":
                is_valid_style_top.append(style_name)

    return is_valid_style_bottom, is_valid_style_top

def apply_overlap_blue(d, end_times):
    start_time = timestamp_to_centiseconds(d.get("Start"))
    end_time = timestamp_to_centiseconds(d.get("End"))

    apply_on_index = 0
    for i in range(len(end_times) + 1):
        current_end_time = end_times[i] if i < len(end_times) else 0
        if start_time < (current_end_time - CENTISECOND_LENIENCY): # correct for within the frame (within 5 centiseconds for a bit extra there shouldn't be one frame gaps anyways)
            apply_on_index = i + 1
        else:
            try:
                end_times[i] = end_time
            except IndexError:
                end_times.append(end_time)
            break

    if apply_on_index % 2 != 0: # On odd indexes add overlap color
        color_tag = "{\\3c" + COLOR_HEX + "}"
        d["Text"] = color_tag + d["Text"]

    line = (dict2line(d))

    return line

def apply(lines_list, is_valid_style_bottom, is_valid_style_top):
    bottom_end_times = [0]
    top_end_times = [0]

    for line_idx, line in enumerate(lines_list):
        if not line.startswith("Dialogue: "):
            continue

        d = line2dict(line)

        # Top track
        if (d.get("Style") in is_valid_style_top and not any(keyword in d.get("Text", "") \
            for keyword in ["\\an", "\\pos", "\\move"]) or ("\\an8" in d.get("Text")) and "Subtitle" in d.get("Style")):
            lines_list[line_idx] = apply_overlap_blue(d, top_end_times)

        # Bottom track
        elif d.get("Style") in is_valid_style_bottom and not any(keyword in d.get("Text", "") \
            for keyword in ["\\an", "\\pos", "\\move"]):
            lines_list[line_idx] = apply_overlap_blue(d, bottom_end_times)

def main(inpath, outpath):
    with open(inpath, encoding="utf-8") as infile:
        lines_list = infile.readlines()

    is_valid_style_bottom, is_valid_style_top = generate_styles_list(lines_list)
    apply(lines_list, is_valid_style_bottom, is_valid_style_top)

    with open(outpath, "w", encoding="utf-8") as outfile:
        outfile.writelines(lines_list)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"Usage: {sys.argv[0]} infile.ass outfile.ass")

    main(sys.argv[1], sys.argv[2])
