# Regex Stuff V2.5
import sys
import re

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

def fix_incorrect_songs_style(lines_list):
    # Hidive-downloader-nx sometimes incorrect assigns styles, this is a problem with the downloader not hidive.

    DEFAULT_CAPTIONS_STYLE = "Style: Caption-Default,Swis721 BT,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,1,2,2,20,20,20,1\n"

    add_default_style = False
    for line_idx, line in enumerate(lines_list):
        if line.startswith("Dialogue:"):
            d = line2dict(line)
            if "Song" in d["Style"] and "\\pos" in d["Text"]:
                d["Style"] = "Caption-Default"
                add_default_style = True
            lines_list[line_idx] = dict2line(d)

    if add_default_style:
        line_idx = 0
        while lines_list[line_idx] != "[V4+ Styles]\n":
            line_idx += 1

        while lines_list[line_idx] != "\n":
            line_idx += 1

        lines_list.insert(line_idx, DEFAULT_CAPTIONS_STYLE)

def apply_fix(lines_list, modification_func):
    for line_idx, line in enumerate(lines_list):
        if line.startswith("Dialogue:"):
            d = line2dict(line)
            lines_list[line_idx] = dict2line(modification_func(d))

def add_song_fad(d):
    if "Song" in d["Style"] and "{\\fad(150,150)}" not in d["Text"]:
        d["Text"] = "{\\fad(150,150)}" + d["Text"]
    return d

def fix_em_dash(d):
    # Dash with a space before it is usually em-dash for punctuation.
    # The space should be removed before the general replace in the last line
    if not (re.search(r"\s-[A-Za-z]", d["Text"]) or re.search(r"\}-[A-Za-z]", d["Text"]) or d["Text"].startswith("-")): # Not Caption line that is -Title of Something-
        d["Text"] = d["Text"].replace("--", "—")
        if not d["Style"].startswith("Caption"):
            d["Text"] = d["Text"].replace(" - ", "—")
            d["Text"] = d["Text"].replace(" -\\N", "—\\N")
            d["Text"] = d["Text"].replace("-\\N", "—\\N")
            #d["Text"] = d["Text"].replace(" -([\"“”'’])", "—\1")
            d["Text"] = re.sub(" -([\"“”'’])", "—\\1", d["Text"])
            d["Text"] = re.sub("-([\"“”'’])", "—\\1", d["Text"])
        d["Text"] = d["Text"].replace("-?", "—?")
        d["Text"] = d["Text"].replace("-!", "—!")
        d["Text"] = d["Text"].replace(" - \n", "— \n")
        d["Text"] = d["Text"].replace(" -\n", "—\n")
        d["Text"] = d["Text"].replace("- \n", "— \n")
        d["Text"] = d["Text"].replace("-\n", "—\n")
        d["Text"] = d["Text"].replace("\\N- ", "\\N—")
        # d["Text"] = d["Text"].replace("\\N-", "\\N—") # Could be false positive
        if not d["Style"].startswith("Caption"):
            d["Text"] = d["Text"].replace("- ", "— ")
    return d

def fix_long_lines(d):
    # If 3 liner or more then get rid of new lines chars
    # Important that this program is run after Hidive splitter

    if not "}-" in d["Text"]: # Caption line that is -Title of Something-
        if not d["Style"].startswith("Caption"):
            pattern = re.compile(r"\\N")
            occurrences = pattern.findall(d["Text"])
            if len(occurrences) >= 2:
                d["Text"] = re.sub(r"\\N", " ", d["Text"])

    return d

def fix_interrobang(d):
    # Replace !? with ?!

    d["Text"] = re.sub(r"(?<![?!])(!\?)", r"?!;q;", d["Text"])
    for i in range(20): # For odd ammounts like !?! -> ?!?
        d["Text"] = re.sub(r"(?<=[?!])(;q;[!?])", r"?;e;", d["Text"])
        d["Text"] = re.sub(r"(?<=[?!])(;e;[!?])", r"!;q;", d["Text"])
    d["Text"] = d["Text"].replace(";q;", "")
    d["Text"] = d["Text"].replace(";e;", "")

    return d

def fix_symbols(d):
    d["Text"] = re.sub("‘", "'", d["Text"])
    d["Text"] = re.sub("’", "'", d["Text"])
    d["Text"] = re.sub("“", '"', d["Text"])
    d["Text"] = re.sub("”", '"', d["Text"])

    return d

def fix_layers(d):
    if not d["Style"].startswith("Caption"):
        d["Layer"] = "10"

    return d

def main(inpath, outpath):
    lines_list = list()
    with open(inpath, encoding="utf-8") as infile:
        lines_list = infile.readlines()

    # fix_incorrect_songs_style(lines_list)
    apply_fix(lines_list, add_song_fad)
    apply_fix(lines_list, fix_em_dash)
    apply_fix(lines_list, fix_long_lines)
    apply_fix(lines_list, fix_interrobang)
    apply_fix(lines_list, fix_symbols)
    apply_fix(lines_list, fix_layers)

    with open(outpath, "w", encoding="utf-8") as outfile:
        outfile.writelines(lines_list)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"Usage: {sys.argv[0]} infile.ass outfile.ass")

    main(sys.argv[1], sys.argv[2])