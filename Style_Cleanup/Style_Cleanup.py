# Style_Cleanup V1.5

import sys
import re

DEFAULT_STYLE = "SPOverrideF,50,&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,-1,0,0,0,100,100,0,0,1,2.4,1,2,40,40,40,1"
ALT_STYLE = "SPOverrideF,50,&H00FFFFFF,&H00FFFFFF,&H00743E15,&HA0000000,-1,0,0,0,100,100,0,0,1,2.4,1,2,40,40,40,1"
OVERLAP_TAG = "{\\3c&H743E15&}"

def event_to_dict(line):
    line_pattern = re.compile(r"(?P<Format>[^:]*): ?(?P<Layer>\d*), ?(?P<Start>[^,]*), ?(?P<End>[^,]*), ?(?P<Style>[^,]*), ?(?P<Name>[^,]*), ?(?P<MarginL>[^,]*), ?(?P<MarginR>[^,]*), ?(?P<MarginV>[^,]*), ?(?P<Effect>[^,]*),(?P<Text>.*)")
    match = line_pattern.match(line)
    return {key: match.group(key) for key in line_pattern.groupindex}


def dict_to_event(d):
    return f"{d['Format']}: {d['Layer']},{d['Start']},{d['End']},{d['Style']},{d['Name']},{d['MarginL']},{d['MarginR']},{d['MarginV']},{d['Effect']},{d['Text']}"


def style_to_dict(line):
    line_pattern = re.compile(
        r"(?P<Format>[^:]*): ?(?P<Name>[^,]*), ?(?P<Fontname>[^,]*), ?(?P<Fontsize>[^,]*), ?(?P<PrimaryColour>[^,]*), ?(?P<SecondaryColour>[^,]*), ?(?P<OutlineColour>[^,]*), ?(?P<BackColour>[^,]*), ?(?P<Bold>[^,]*), ?(?P<Italic>[^,]*), ?(?P<Underline>[^,]*), ?(?P<StrikeOut>[^,]*), ?(?P<ScaleX>[^,]*), ?(?P<ScaleY>[^,]*), ?(?P<Spacing>[^,]*), ?(?P<Angle>[^,]*), ?(?P<BorderStyle>[^,]*), ?(?P<Outline>[^,]*), ?(?P<Shadow>[^,]*), ?(?P<Alignment>[^,]*), ?(?P<MarginL>[^,]*), ?(?P<MarginR>[^,]*), ?(?P<MarginV>[^,]*), ?(?P<Encoding>.*)"
    )
    match = line_pattern.match(line)
    return {key: match.group(key) for key in line_pattern.groupindex}


def dict_to_style(d):
    return f"Style: {d['Name']},{d['Fontname']},{d['Fontsize']},{d['PrimaryColour']},{d['SecondaryColour']},{d['OutlineColour']},{d['BackColour']},{d['Bold']},{d['Italic']},{d['Underline']},{d['StrikeOut']},{d['ScaleX']},{d['ScaleY']},{d['Spacing']},{d['Angle']},{d['BorderStyle']},{d['Outline']},{d['Shadow']},{d['Alignment']},{d['MarginL']},{d['MarginR']},{d['MarginV']},{d['Encoding']}"


def generate_styles_list(lines_list):
    styles_list = []
    for line in lines_list:
        if line.startswith("Style: "):
            styles_list.append(line.strip("\n"))

    return styles_list


def generate_events_list(lines_list):
    events_list = []
    for line in lines_list:
        if line.startswith("Dialogue: "):
            events_list.append(line.strip("\n"))

    return events_list


def compare_dictionaries(dict1, dict2, exclude_keys=[]):
    filtered_dict1 = {k: v for k, v in dict1.items() if k not in exclude_keys}
    filtered_dict2 = {k: v for k, v in dict2.items() if k not in exclude_keys}

    return filtered_dict1 == filtered_dict2


def map_styles_with_inline_tags(styles):

    style_inline = {}

    for style in styles:
        style_dict = style_to_dict(style)

        if "Subtitle" in style_dict["Name"]:
            default_style_dict = style_to_dict(f"Style: Default,{DEFAULT_STYLE}")
            style_inline[style_dict["Name"]] = ""

            if str(style_dict["Alignment"]) == "8":
                style_inline[style_dict["Name"]] += r"\an8"
            if str(style_dict["Italic"]) == "-1":
                style_inline[style_dict["Name"]] += r"\i1"
            if str(style_dict["Underline"]) == "-1":
                style_inline[style_dict["Name"]] += r"\u1"
            if int(style_dict["Fontsize"]) != int(default_style_dict["Fontsize"]) and str(style_dict["Fontname"]) == str(default_style_dict["Fontname"]):
                style_inline[style_dict["Name"]] += r"\fs" + style_dict["Fontsize"]

        elif "Song" in style_dict["Name"] and "SongCap" not in style_dict["Name"]:
            style_inline[style_dict["Name"]] = ""

        elif "Cap" in style_dict["Name"]:
            style_inline[style_dict["Name"]] = f"\\fn{style_dict['Fontname']}\\fs{style_dict['Fontsize']}\\c&H{style_dict['PrimaryColour'][-6:]}&"
            if str(style_dict["Italic"]) == "-1":
                style_inline[style_dict["Name"]] += r"\i1"
            if str(style_dict["Underline"]) == "-1":
                style_inline[style_dict["Name"]] += r"\u1"

    return style_inline


def update_styles_and_inline_tags(styles, events, style_inline):
    default_style_dict = style_to_dict(f"Style: Default,{DEFAULT_STYLE}")

    has_alt = False
    for event in events:
        if "{\\3c&H743E15&}" in event:
            has_alt = True
            break

    fallback_style_count = 0
    subtitle_other_font_dict = {}

    for index, style in enumerate(styles):
        style_dict = style_to_dict(style)

        if "Subtitle" in style_dict["Name"]:
            style_dict["Alignment"] = "2"
            style_dict["Italic"] = "0"
            style_dict["Underline"] = "0"
            style_dict["MarginL"] = default_style_dict["MarginL"]
            style_dict["MarginR"] = default_style_dict["MarginR"]
            style_dict["MarginV"] = default_style_dict["MarginV"]
            if int(style_dict["Fontsize"]) != int(default_style_dict["Fontsize"]) and str(style_dict["Fontname"]) == str(default_style_dict["Fontname"]):
                style_dict["Fontsize"] = default_style_dict["Fontsize"]
            temp_style_name = style_dict["Name"]
            style_dict["Name"] = "Subtitle"

            if style_dict["Fontname"] != default_style_dict["Fontname"]:
                style_dict["Name"] = style_dict["Fontname"]
                try:
                    break_flag = False
                    for i, stored_style in enumerate(subtitle_other_font_dict[style_dict["Fontname"]]):
                        if compare_dictionaries(style_dict, stored_style, exclude_keys=["Name"]):
                            f_count = i + 1
                            break_flag = True
                            break
                    if not break_flag:
                        subtitle_other_font_dict[style_dict["Fontname"]].append(style_dict)
                        f_count = len(subtitle_other_font_dict[style_dict["Fontname"]])
                except Exception as e:
                    subtitle_other_font_dict[style_dict["Fontname"]] = [style_dict]
                    f_count = 1
                style_dict["Name"] = f"Subtitle-{style_dict['Fontname']}-{f_count}"
            elif not compare_dictionaries(style_dict, default_style_dict, exclude_keys=
                                    ["Name", "Fontsize", "Alignment", "Italic", "Underline", "MarginL", "MarginR", "MarginV"]):
                fallback_style_count += 1
                style_dict["Name"] = "Subtitle-" + str(fallback_style_count)

            styles[index] = dict_to_style(style_dict)

            for i, event in enumerate(events):
                event_dict = event_to_dict(event)
                if event_dict["Style"] == temp_style_name:
                    if OVERLAP_TAG in event_dict["Text"]:
                        event_dict["Style"] = "Subtitle-Alt"
                        event_dict["Text"] = event_dict["Text"].replace(OVERLAP_TAG, "")
                    else:
                        event_dict["Style"] = style_dict["Name"]
                    if style_inline[temp_style_name]:
                        event_dict["Text"] = f"{{{style_inline[temp_style_name]}}}{event_dict['Text']}"  # prepend text with inline tags
                    events[i] = dict_to_event(event_dict)

        elif "Song" in style_dict["Name"] and "SongCap" not in style_dict["Name"]:
            style_dict["Name"] = "Song"
            styles[index] = dict_to_style(style_dict)

            for i, event in enumerate(events):
                event_dict = event_to_dict(event)
                if "Song" in event_dict["Style"]:
                    event_dict["Style"] = "Song"
                    events[i] = dict_to_event(event_dict)

        elif "Cap" in style_dict["Name"]:
            temp_style_name = style_dict["Name"]
            if "Caption" in style_dict["Name"]:
                style_dict["Name"] = "Caption"
            elif "SongCap" in style_dict["Name"]:
                style_dict["Name"] = "SongCap"
            style_dict["Fontname"] = default_style_dict["Fontname"]
            style_dict["Fontsize"] = default_style_dict["Fontsize"]
            style_dict["PrimaryColour"] = default_style_dict["PrimaryColour"]
            style_dict["SecondaryColour"] = default_style_dict["SecondaryColour"]
            style_dict["Alignment"] = "7"
            style_dict["Italic"] = "0"
            style_dict["Underline"] = "0"

            styles[index] = dict_to_style(style_dict)

            for i, event in enumerate(events):
                event_dict = event_to_dict(event)
                if event_dict["Style"] == temp_style_name:
                    event_dict["Style"] = style_dict["Name"]
                    if style_inline[temp_style_name]:
                        if event_dict["Text"].count("{\\an7}") > 0:
                            event_dict["Text"] = event_dict["Text"].replace("{\\an7}", "")
                        else:
                            event_dict["Text"] = "{\\an8}" + event_dict["Text"]
                        event_dict["Text"] = f"{{{style_inline[temp_style_name]}}}{event_dict['Text']}"  # prepend text with inline tags
                        event_dict["Text"] = event_dict["Text"].replace("}{", "")
                    events[i] = dict_to_event(event_dict)

    if has_alt:
        styles.append(f"Style: Subtitle-Alt,{ALT_STYLE}")

    new_styles = []
    for i in styles:
        if i not in new_styles and not i.startswith("Style: Default"):
            new_styles.append(i)
    styles.clear()
    styles.extend(new_styles)


def sort_styles(styles):
    def custom_sort_key(style):
        if "Subtitle" in style and "Alt" not in style:
            return (0, style)
        if "Alt" in style:
            return (1, style)
        if "Song" in style and "SongCap" not in style:
            return (2, style)
        if "Cap" in style:
            return (3, style)
        return (4, style)

    styles.sort(key=custom_sort_key)


def update_lines_list(lines_list, styles, events):
    new_styles = [style + "\n" for style in styles]
    new_events = [event + "\n" for event in events]
    out_list = [line for line in lines_list if not line.startswith("Style: ")]
    out_list = [line for line in out_list if not line.startswith("Dialogue: ")]

    for idx, line in enumerate(out_list):
        if line.startswith("Format: Name, Fontname, Fontsize"):
            index_of_styles = idx + 1
            break
    out_list = out_list[:index_of_styles] + new_styles + out_list[index_of_styles:]

    for idx, line in enumerate(out_list):
        if line.startswith("Format: Layer, Start, End"):
            index_of_events = idx + 1
            break
    out_list = out_list[:index_of_events] + new_events + out_list[index_of_events:]

    return out_list


def main(inpath, outpath):
    with open(inpath, encoding="utf-8") as infile:
        lines_list = infile.readlines()

    styles = generate_styles_list(lines_list)
    events = generate_events_list(lines_list)
    style_inline = map_styles_with_inline_tags(styles)
    update_styles_and_inline_tags(styles, events, style_inline)
    sort_styles(styles)
    out_list = update_lines_list(lines_list, styles, events)

    with open(outpath, "w", encoding="utf-8") as outfile:
        outfile.writelines(out_list)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"Usage: {sys.argv[0]} infile.ass outfile.ass")

    main(sys.argv[1], sys.argv[2])