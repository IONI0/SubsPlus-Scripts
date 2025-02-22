# Converter V1.6

import sys
import copy
from datetime import timedelta
import ass
from ass.data import Color as Color

def set_info(doc):
    doc.info["Title"] = "[SubsPlus+]"
    doc.info["YCbCr Matrix"] = "TV.709"
    try:
        doc.info.pop("LayoutResX")
        doc.info.pop("LayoutResY")
    except KeyError:
        pass

def sort_signs(obj):
    if "\\pos" in obj.text:
        return 1
    else:
        return 0


def detect_styles(doc):
    def gen_style(style, event):
        new_style_num = style_num

        # Identify style type
        if "\\pos" in event.text:
            type = "Caption"
        else:
            type = "Subtitle"

        try:
            # Already mapped
            style_name = style_map[event.style][type]
        except:
            # Do the mapping
            if type == "Subtitle":
                # If the other type is already in, then it's a double type style
                try:
                    style_map[event.style]["Caption"]
                    # 900 styles for duplicates
                    style_name = f"Subtitle-{style_num + 900}"
                except KeyError:
                    style_name = f"Subtitle-{style_num}"
                    new_style_num += 1
                new_style = copy.deepcopy(style)
                new_style.name = style_name
                subtitle_styles.append(new_style)
            elif type == "Caption":
                try:
                    style_map[event.style]["Subtitle"]
                    style_name = f"Caption-{style_num + 900}"
                except KeyError:
                    style_name = f"Caption-{style_num}"
                    new_style_num += 1
                new_style = copy.deepcopy(style)
                new_style.name = style_name
                caption_styles.append(new_style)

            try:
                style_map[event.style][type] = style_name
            except:
                style_map[event.style] = {}
                style_map[event.style][type] = style_name

        event.style = style_name
        return new_style_num

    # Should match with the Q style number
    style_num = 0
    subtitle_styles = []
    caption_styles = []
    # Key = Q style, Value = new style
    style_map = {}
    for style in doc.styles:
        for event in doc.events:
            if style.name == event.style:
                style_num = gen_style(style, event)

    doc.styles = subtitle_styles
    doc.styles.extend(caption_styles)


def song_detection(doc):
    # Figure out which styles are songs

    # Pass 1: 9 consecutive lines (Additive)
    possible_song_styles = [style.name for style in doc.styles if "Subtitle" in style.name and style.fontsize == 40]

    consecutive_lines = 0
    styles_involved = set()
    song_styles = set()
    for event in doc.events:
        if event.style not in possible_song_styles:
            consecutive_lines = 0
            styles_involved = set()
            continue
        consecutive_lines += 1
        styles_involved.add(event.style)
        if consecutive_lines > 8 and event.style not in song_styles:
            # song_styles.update(styles_involved)
            song_styles.add(event.style)

    # Pass 2: Time based 7 consecutive (Additive)

    for style in possible_song_styles:
        consecutive_events = 0
        allowed_pauses = 1
        last_event_end = timedelta(0)
        for event in doc.events:
            if event.style != style:
                continue
            time_difference = event.start - last_event_end
            if time_difference < timedelta(seconds=1):
                # if they are consecutive within 1 second
                consecutive_events += 1
                if consecutive_events == 7: # arbritary amount
                    song_styles.add(style)
                    break
            elif time_difference < timedelta(seconds=5)and allowed_pauses > 0:
                allowed_pauses -= 1
                consecutive_events += 1
                if consecutive_events == 7: # arbritary amount
                    song_styles.add(style)
                    break
            else:
                consecutive_events = 0
                allowed_pauses = 1
            last_event_end = event.end

    # Pass 3: Fill Gap (Additive)
    last_event_end = timedelta(seconds=-50)
    for event in doc.events:
        if event.style not in song_styles:
            continue
        time_difference = event.start - last_event_end
        if time_difference < timedelta(seconds=10) and time_difference > timedelta(seconds=0):
            # Gap found, look for song events inside
            for inside_event in doc.events:
                if inside_event.style not in possible_song_styles:
                    continue
                if not (inside_event.start >= last_event_end and inside_event.end <= event.start):
                    continue
                print(f"Gap filled: {inside_event.text}")
                song_styles.add(inside_event.style)
        last_event_end = event.end

    # Pass 4: Subset styles (Additive)
    # Basically for when they do romaji and english at the same time

    remaining_contenders = [item for item in possible_song_styles if item not in song_styles]

    song_styles_times = [] # List of list (each style) of tuple: (event.start, event.end)
    for style in song_styles:
        style_times = []
        for event in doc.events:
            if event.style != style:
                continue
            style_times.append((event.start, event.end))
        song_styles_times.append(style_times)

    remaining_contenders_times = {}
    for style in remaining_contenders:
        style_times = []
        for event in doc.events:
            if event.style != style:
                continue
            style_times.append((event.start, event.end))
        remaining_contenders_times[style] = style_times

    # Find subsets
    for remaining_style_key in remaining_contenders_times:
        remaining_style_value = remaining_contenders_times[remaining_style_key]
        for song_style in song_styles_times:
            if all(item in song_style for item in remaining_style_value):
                print(f"By Subset: {remaining_style_key}")
                song_styles.add(remaining_style_key)

    # Update style
    for style in doc.styles:
        if style.name in song_styles:
            style.name = style.name.replace("Subtitle", "Song")

    # Update events
    for event in doc.events:
        if event.style in song_styles:
            event.style = event.style.replace("Subtitle", "Song")


def restrictive_song_detection(doc):
    song_style = ass.Style(name='Song', fontname='Sub Alegreya', fontsize=46, primary_color=Color(r=0xff, g=0xff, b=0xff, a=0x00), secondary_color=Color(r=0xff, g=0xff, b=0xff, a=0x00), outline_color=Color(r=0x72, g=0x0c, b=0x5f, a=0x00), back_color=Color(r=0x00, g=0x00, b=0x00, a=0xa0), bold=True, italic=False, underline=False, strike_out=False, scale_x=100.0, scale_y=100.0, spacing=0.1, angle=0.0, border_style=1, outline=2.2, shadow=0, alignment=8, margin_l=100, margin_r=100, margin_v=25, encoding=1)
    possible_song_styles = [style.name for style in doc.styles if "Subtitle" in style.name and style.fontsize == 40]

    song_blocks = [] # Blocks of song events

    # Find all blocks of song events (More than 8 consecutive an8)
    consecutive_lines = 0
    events_involved = []
    for event in doc.events:
        if event.style not in possible_song_styles:
            if consecutive_lines > 8:
                song_blocks.append(events_involved)
            consecutive_lines = 0
            events_involved = []
            continue
        consecutive_lines += 1
        events_involved.append(event)

    if len(song_blocks) == 0:
        return

    # Add Song style to styles
    insert_pos = len(doc.styles)
    for idx, style in enumerate(doc.styles):
        if "Caption" in style.name:
            insert_pos = idx
            break
    doc.styles.insert(insert_pos, song_style)

    for event in song_blocks[0]:
        event.style = "Song"

    if len(song_blocks) >= 2:
        # Skip doing middle song blocks. Since hopefully ED will be the last one
        for event in song_blocks[-1]:
            event.style = "Song"


def manual_caption2song(doc):
    pass


def rescale_captions(doc):
    for style in doc.styles:
        if "Caption" in style.name:
            style.fontsize = round(style.fontsize / 1.2 * 1.125)


def restyler(doc):
    for style in doc.styles:
        if "Subtitle" in style.name:
            style.primary_color = Color.from_ass("&H00FFFFFF")
            style.secondary_color = Color.from_ass("&H00FFFFFF")
            style.outline_color = Color.from_ass("&H00000000")
            style.back_color = Color.from_ass("&HA0000000")
            style.bold = True
            style.outline = 2.4
            style.shadow = 1
            style.margin_l = 40
            style.margin_r = 40
            style.margin_v = 40
            if style.fontname == "Swis721 BT":
                if style.fontsize == 40:
                    style.alignment = 8
                if style.fontsize == 48 or style.fontsize == 40:
                    style.fontsize = 50
                style.fontname = "SPOverrideF"
            elif style.fontname == "Chiller" and style.fontsize < 63: # Change later
                # send to an8
                pass
        elif "Song" in style.name:
            style.fontname = "Sub Alegreya"
            style.fontsize = 46
            style.primary_color = Color.from_ass("&H00FFFFFF")
            style.secondary_color = Color.from_ass("&H00FFFFFF")
            style.outline_color = Color.from_ass("&H005F0C72")
            style.back_color = Color.from_ass("&HA0000000")
            style.bold = True
            style.spacing = 0.1
            style.outline = 2.2
            style.shadow = 0
            style.margin_l = 40
            style.margin_r = 40
            style.margin_v = 25
            style.alignment = 8
        elif "Caption" in style.name:
            if style.primary_color.to_ass() == "&H0094FDFF":
                style.primary_color = Color.from_ass("&H0000FFFF")
                style.secondary_color = Color.from_ass("&H0000FFFF")
            style.outline = 1
            style.shadow = 1
            style.margin_l = 20
            style.margin_r = 20
            style.margin_v = 20
            # style.spacing = 0.01


def fix_small_font_shenanigans(doc):
    # Fix times where it is going subtitle font size 48 -> 40 -> 32 as an effect

    styles_by_name = {style.name: style for style in doc.styles}

    for i, event in enumerate(doc.events):
        style = styles_by_name.get(event.style)
        if not (style and style.alignment == 8 and "Subtitle" in style.name):
            continue

        if i + 1 < len(doc.events):
            next_event = doc.events[i + 1]
            next_style = styles_by_name.get(next_event.style)
            if not ("Subtitle" in next_style.name and next_style.fontsize < 40):
                continue
            small_style = copy.deepcopy(style)
            small_style.name = "Subtitle-Small"
            small_style.alignment = 2
            small_style.fontsize = 40
            doc.styles.append(small_style)
            event.style = "Subtitle-Small"



def main(inpath, outpath):
    with open(inpath, encoding='utf_8_sig') as f:
        doc = ass.parse(f)

    set_info(doc)
    doc.events = sorted(doc.events, key=sort_signs)
    detect_styles(doc)
    song_detection(doc)
    # restrictive_song_detection(doc)
    restyler(doc)
    fix_small_font_shenanigans(doc)
    rescale_captions(doc)

    with open(outpath, "w", encoding='utf_8_sig') as f:
        doc.dump_file(f)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"Usage: {sys.argv[0]} infile.ass outfile.ass")
    main(sys.argv[1], sys.argv[2])
