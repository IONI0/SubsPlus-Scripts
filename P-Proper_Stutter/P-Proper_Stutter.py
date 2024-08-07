# P-Proper_Stutter V2.3
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

def two_letter_fix(words):
    for x in range(20):
        words = re.sub(r"(?<!\w)([Ww])-([Ww]h)", "\\1h-\\2", words)
        words = re.sub(r"(?<!\w)([Ss])-([Ss]h)", "\\1h-\\2", words)
        words = re.sub(r"(?<!\w)([Tt])-([Tt]h)", "\\1h-\\2", words)
        
    return words

def one_letter_stutter(letters, a):
    if letters[1+a] == "-" and letters[0+a].lower() == letters[2+a].lower():
        letters[2+a] = letters[2+a].upper()
        # Y-y-y-you
        try:
            b = 3 + a
            while True:
                if letters[b] == "-" and letters[b-1].lower() == letters[b+1].lower():
                    letters[b+1] = letters[b+1].upper()
                    b += 2
                else:
                    break
        except IndexError:
            pass
    
    return letters

def two_letter_stutter(letters, a):
    letters[3+a] = letters[3+a].upper()
    # Th-th-th-this
    try:
        b = 5 + a
        while True:
            if letters[b] == "-" and letters[b-2].lower() == letters[b+1].lower() and letters[b-1].lower() == letters[b+2].lower():
                letters[b+1] = letters[b+1].upper()
                b += 3
            else:
                break
    except IndexError:
        pass
    
    return letters
    
def blacklist_only_two_letters(word):
    pattern = r'\b\w*-\w{3,}\b'
    return bool(re.search(pattern, word))

def stutter_fix(word):
    try:
        a = word.find(next(filter(str.isalpha, word))) # Index of first alphabet character
    except:
        a = 0
    letters = [x for x in word] 
    try:
        if letters[0+a].isupper():
            if letters[1+a] == "-" and letters[0+a].lower() == letters[2+a].lower():
                letters = one_letter_stutter(letters, a)
                    
            elif letters[2+a] == "-" and letters[0+a].lower() == letters[3+a].lower() and letters[1+a].lower() == letters[4+a].lower():
                if blacklist_only_two_letters(word):
                    letters = two_letter_stutter(letters, a)
    except:
        pass
    new_word = "".join(letters)
    
    return new_word

def stutter_opperations(words):
    words = words.replace("\\N", " \\N ")
    words = words.replace("}", "} ")
    words = two_letter_fix(words)
    words_ls = words.split(" ") # W-well,|not|like|I|have|much|choice!
    new_line = []
    for word in words_ls:
        # S..so -> S... So or S-So
        m = re.search(r"(?<!\w)(\w)\.\.(\w)", word)
        try:
            if m.group(1) == m.group(2):
                word = re.sub(r"(?<!\w)(\w)\.\.(\w)", "\\1..\\2", word) # "\\1... \\2" or "\\1-\\2" or "\\1..\\2"
            elif m.group(1).lower() == m.group(2):
                g2 = str(m.group(1).upper())
                word = re.sub(r"(?<!\w)(\w)\.\.(\w)", f"\\1..{g2}", word) # "\\1... {g2}" or "\\1-{g2}" or "\\1..{g2}"
        except:
            pass
        
        # Th..this -> Th..This or Th-This
        m = re.search(r"(?<!\w)(\w{2})\.\.(\w{2})", word)
        try:
            if m.group(1) == m.group(2):
                word = re.sub(r"(?<!\w)(\w{2})\.\.(\w{2})", "\\1..\\2", word) # "\\1... \\2" or "\\1-\\2" or "\\1..\\2"
            elif m.group(1).lower() == m.group(2):
                g2 = str(m.group(1).capitalize())
                word = re.sub(r"(?<!\w)(\w{2})\.\.(\w{2})", f"\\1..{g2}", word)  # "\\1... {g2}" or "\\1-{g2}" or "\\1..{g2}"
        except:
            pass
        
        if "-" in word:
            new_line.append(stutter_fix(word))
        else:
            new_line.append(word)
        
    new_line = " ".join(new_line)
    new_line = new_line.replace(" \\N ", "\\N")
    new_line = new_line.replace("} ", "}")
    
    return new_line

def apply(lines_list):
    for line_idx, line in enumerate(lines_list):
        if line.startswith("Dialogue: "):
            d = line2dict(line)
            d["Text"] = stutter_opperations(d["Text"])   
            lines_list[line_idx] = dict2line(d)
       
def main(inpath, outpath):
    with open(inpath, encoding="utf-8") as infile:
        lines_list = infile.readlines()

    apply(lines_list)
    
    with open(outpath, "w", encoding="utf-8") as outfile:
        outfile.writelines(lines_list)
    
if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"Usage: {sys.argv[0]} infile.ass outfile.ass")

    main(sys.argv[1], sys.argv[2])
