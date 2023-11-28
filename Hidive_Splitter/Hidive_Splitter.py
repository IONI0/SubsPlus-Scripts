# Hidive_Splitter V2.0
import sys
import re

# match an ASS event with named groups and newline on the end
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

def generate_styles_dict(lines_list, styles_dict):
    for line in lines_list:
        if line.startswith("Style: "):
            style_split = line.split(",", 1) 
            style_name = style_split[0].replace("Style: ", "")
            style_info = style_split[1]
            styles_dict[style_name] = style_info

def split_subs(lines_list):
    out_lines = []
    for line in lines_list:
        if line.startswith("Dialogue: "):
            d = line2dict(line)
            if not "Caption" in d["Style"]:
                split_lines(d, out_lines)
            else:
                out_lines.append(line)
        else: 
            out_lines.append(line)
            
    return out_lines
            
def combine_lines(lines_list, styles_dict):
    out_lines = []
    for i in range(len(lines_list)):
        cur_line = lines_list[i]
        if not cur_line.startswith("Dialogue: "):
            out_lines.append(cur_line)
            continue        
        
        has_combined = False 
        for j in range(1, 6): # Check 5 previous elements
            check_line = out_lines[-j]
            if check_line.startswith("Dialogue: "):
                check_line = line2dict(check_line)
            else:
                continue
            has_combined = combine(line2dict(cur_line), check_line, out_lines, styles_dict)
            if has_combined:
                break
        
        if not has_combined:
            out_lines.append(cur_line)
    
    return out_lines
    
def split_lines(line_dict, lines_list):
    # Split a particular line
    # Need to be inversed to preserve render positions
    result = []
    line_split = line_dict["Text"].split("\\N")
    add_style = line_dict["Style"]
    add_line = ""
    
    for line in line_split:
        if re.search(r"\\r(.*?)}", line):
            new_style = re.search(r"\\r(.*?)}", line).group(1)
            line = re.search(r"}(.*?){", line).group(1)
        else:
            new_style = line_dict["Style"]
        
        if add_style == new_style:
            add_line += line + "\\N"
        else:
            # Add everything before in
            line_dict["Style"] = add_style
            line_dict["Text"] = add_line.rstrip("\\N").rstrip("\n") + "\n"
            result.append(dict2line(line_dict))
            
            add_style = new_style
            add_line = line           
            
    line_dict["Style"] = add_style
    line_dict["Text"] = add_line.rstrip("\\N").rstrip("\n") + "\n"
    result.append(dict2line(line_dict))
    result.reverse()
    lines_list.extend(result)

def combine(line, check, lines_list, styles_dict):
    if check["Text"] == line["Text"] and styles_dict[check["Style"]] == styles_dict[line["Style"]]: # If line is the same as the last line (first one)
        if check["End"] == line["Start"]: # If they are adjacent
            line["Start"] = check["Start"] # Combine lines
            for x in range(1, 8): # Arbritrary lookback amount
                if lines_list[-x] == dict2line(check): 
                    lines_list[-x] = dict2line(line)
                    return True
    return False
            
def reorder_simultaneous_lines(lines_list):
    # Adjust which simulataneous lines are top and bottom
    # Unused as it could mess with speaker order
    mem_start = -1
    mem_end = -1
    for x, line in enumerate(lines_list):
        if line.startswith("Dialogue: "):  
            d = line2dict(line)
            if d["Style"].startswith("Subtitle"):
                start = timestamp_to_centiseconds(d["Start"])
                end = timestamp_to_centiseconds(d["End"])
                
                if start == mem_start and end != mem_end:
                    if mem_end < end:
                        last_line = lines_list[x-1]
                        lines_list[x-1] = lines_list[x]
                        lines_list[x] = last_line
                    
                mem_start = start
                mem_end = end
        
def main(inpath, outpath):
    lines_list = []
    styles_dict = {}
    with open(inpath, encoding="utf-8") as infile:
        lines_list = infile.readlines()
        
    generate_styles_dict(lines_list, styles_dict)

    subs_split = split_subs(lines_list)
    final_lines = combine_lines(subs_split, styles_dict)
            
    with open(outpath, "w", encoding="utf-8") as outfile:
        outfile.writelines(final_lines)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"Usage: {sys.argv[0]} infile.ass outfile.ass")
        
    main(sys.argv[1], sys.argv[2])