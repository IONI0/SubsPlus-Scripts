# Auto Chap V2.1
import sys
import json
import os
import urllib
import time
import warnings
import argparse
import shutil
from pathlib import Path
import requests

import librosa
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt

### Chapter Names
PRE_OP = "Prologue"
OPENING = "Opening"
EPISODE = "Episode"
ENDING = "Ending"
POST_ED = "Epilogue"

warnings.filterwarnings("ignore", category=FutureWarning) 
warnings.filterwarnings("ignore", category=UserWarning)

def parse_args():
    parser = argparse.ArgumentParser(description="Automatic anime chapter generator using animethemes.")
    parser.add_argument(
        "--input", "-i", type=Path, required=True,
        help="Video/Audio file.",
    )
    
    parser.add_argument(
        "--search-name", "-s", type=str,
        help="Search to pass to animethemes.moe Example: Spy Classroom Season 2. To only use themes that are already downloaded, don't add this argument.",
    )
    
    parser.add_argument(
        "--work-path", "-w", type=Path,
        help="Place to create a .themes folder for storing persistant information per series. Defaults to where the episode is.",
    )
    
    parser.add_argument(
        "--output", "-o", type=Path,
        help="Output chapter file. Defaults to where the episode is.",
    )
    
    parser.add_argument(
        "--delete-themes", "-d", default=False, action="store_true",
        help="Delete the themes and charts after running.",
    )
    
    parser.add_argument(
        "--charts", "-c", default=False, action="store_true",
        help="Make charts of where themes are matched in the episode. They can almost double processing time in some cases though.",
    )
    
    args = parser.parse_args()
    args.no_download = False
    
    if args.search_name is None:
        args.no_download = True
    
    if args.work_path is None:
        args.work_path = Path(os.path.dirname(args.input))
        
    if args.output is None:
        args.output = args.input.with_name(args.input.stem + ".chapters.txt")
        
    return args

def make_folders(work_path):
    subdirectory_path = work_path / ".themes" / "charts"
    shutil.rmtree(subdirectory_path, ignore_errors=True)
    subdirectory_path.mkdir(parents=True)

def get_series_json(search_name):
    global_search = requests.get(f"https://api.animethemes.moe/search?q={urllib.parse.quote(search_name)}").json()
    series_slug = global_search["search"]["anime"][0]["slug"]
    series_json = requests.get(f"https://api.animethemes.moe/anime/{series_slug}?include=animethemes.animethemeentries.videos.audio").json()
    return series_json["anime"]

def download_themes(t_path, series_json):
    print(f'Animethemes matched series: {series_json["name"]}', file=sys.stderr)
    try:
        with open(os.path.join(t_path, "data.json")) as data:
            stored_data = json.load(data)
    except:
        stored_data = {}
    
    # Reset themes if series different from last time 
    if stored_data.get("series_name") != series_json["name"]:
        stored_data = {"series_name": series_json["name"]}
        files = os.listdir(t_path)
        for file in files:
            if file.endswith(".ogg"):
                file_path = os.path.join(t_path, file)
                os.remove(file_path)
    
    for theme in series_json["animethemes"]:
        break_flag = False
        if theme["sequence"] == None:
            cur_theme = theme["type"] + "1" 
        else:
            cur_theme = theme["type"] + str(theme["sequence"]) # OP1 or ED3, etc.
        for version in theme["animethemeentries"]: # Different video versions of theme, no audio difference (I think)
            if break_flag: 
                break
            for video in version["videos"]:
                
                if video["overlap"] == "None": # No overs or transitions
                    try: 
                        if video["audio"]["updated_at"] == stored_data[cur_theme]:
                            break_flag = True
                            print(f"Already have {cur_theme}, skipping download", file=sys.stderr)
                            break
                    except:
                        pass
                    
                    stored_data[cur_theme] = video["audio"]["updated_at"]  
                    response = requests.get(video["audio"]["link"])
                    if response.status_code == 200:
                        with open(f'{t_path}/{cur_theme}.ogg', "wb") as file:
                            file.write(response.content)
                        print(f"{cur_theme} downloaded", file=sys.stderr)
                    else:
                        print("Failed to download video. Status code:", response.status_code, file=sys.stderr)
                        
                    break_flag = True # Continue to next theme
                    break
                           
    with open(os.path.join(t_path, "data.json"), "w") as outfile:
        json.dump(stored_data, outfile)

def find_offset(within_file, find_file, t_path, make_charts, window = 30): # Change window size for accuracy
    try:
        y_within, sr_within = librosa.load(within_file, sr=None)
    except:
        print("Could not load input file", file=sys.stderr)
        sys.exit(1)
    y_find, _ = librosa.load(find_file, sr=sr_within)
    
    theme_name = os.path.splitext(find_file.name)[0]

    try:
        c = signal.correlate(y_within, y_find[:sr_within*window], mode="valid", method="fft")
    except:
        print(f"{theme_name} Error in correlate. Continuing...", file=sys.stderr)
        return None, None
    
    peak = np.argmax(c)
    score = np.max(c)
    offset = round(peak / sr_within, 2)

    if make_charts:
        try:
            fig, ax = plt.subplots()
            ax.plot(c)
        except:
            print(f"{theme_name} Could not plot figure", file=sys.stderr)
    
    duration = librosa.get_duration(filename=find_file)
    
    if score > 1000: # To prevent false positives. Number is a bit arbitrary 
        print(f"{theme_name} matched from {get_timestamp(offset)} -> {get_timestamp(offset + duration)}", file=sys.stderr)
        if make_charts:
            try:
                fig.savefig(os.path.join(f"{t_path}", "charts", f"{theme_name}_matched.png"))
            except:
                print(f"{theme_name} Could not save figure", file=sys.stderr)
        return offset, (offset + duration)
    
    else:
        print(f"{theme_name} not matched", file=sys.stderr)
        if make_charts:
            try:
                fig.savefig(os.path.join(f"{t_path}", "charts", f"{theme_name}.png"))
            except:
                print(f"{theme_name} Could not save figure", file=sys.stderr)
        return None, None
    
def get_timestamp(timesec):
    timestamp = time.strftime(f"%H:%M:%S.{round(timesec%1*1000):03}", time.gmtime(timesec))
    return timestamp

def chapter_validator(offset_list, file_duration):
    if len(offset_list) == 0:
        print("No matches", file=sys.stderr)
        return False
    elif len(offset_list) == 2:
        return True
    elif len(offset_list) == 4:
        if offset_list[0] > (file_duration / 2) and offset_list[2] > (file_duration / 2):
            print("Chapters not valid. They both start in the second half", file=sys.stderr)
            return False
        elif offset_list[0] < (file_duration / 2) and offset_list[2] < (file_duration / 2):
            print("Chapters not valid. They both start in the first half", file=sys.stderr)
            return False
        else:
            return True
    else:
        print("Chapters not valid. Invalid number of offsets", file=sys.stderr)
        return False
        
def generate_chapters(offset_list, file_duration, out_path):
    snapping_distance = 4 # seconds to snap to beginning or end
    
    outfile = open(out_path, "w", encoding="utf-8")
    snap_beginning = False
    snap_end = False
    ed_only = False
    
    if offset_list[0] < snapping_distance:
        snap_beginning = True
    
    if offset_list[-1] > (file_duration - snapping_distance):
        snap_end = True 
        
    if offset_list[0] < (file_duration / 2):
        pass
    else:
        ed_only = True
    
    outfile.write("CHAPTER01=00:00:00.000\n")
    if snap_beginning:
        outfile.write(f"CHAPTER01NAME={OPENING}\n")
        outfile.write(f"CHAPTER02={get_timestamp(offset_list[1])}\n")
        outfile.write(f"CHAPTER02NAME={EPISODE}\n")
        if len(offset_list) == 4:
            outfile.write(f"CHAPTER03={get_timestamp(offset_list[2])}\n")
            outfile.write(f"CHAPTER03NAME={ENDING}\n")
            if not snap_end:
                outfile.write(f"CHAPTER04={get_timestamp(offset_list[3])}\n")
                outfile.write(f"CHAPTER04NAME={POST_ED}\n")
    elif ed_only:
        outfile.write(f"CHAPTER01NAME={EPISODE}\n")
        outfile.write(f"CHAPTER02={get_timestamp(offset_list[0])}\n")
        outfile.write(f"CHAPTER03NAME={ENDING}\n")
        if not snap_end:
            outfile.write(f"CHAPTER03={get_timestamp(offset_list[1])}\n")
            outfile.write(f"CHAPTER03NAME={POST_ED}\n")
    else:
        outfile.write(f"CHAPTER01NAME={PRE_OP}\n")
        outfile.write(f"CHAPTER02={get_timestamp(offset_list[0])}\n")
        outfile.write(f"CHAPTER02NAME={OPENING}\n")
        outfile.write(f"CHAPTER03={get_timestamp(offset_list[1])}\n")
        outfile.write(f"CHAPTER03NAME={EPISODE}\n")
        if len(offset_list) == 4:
            outfile.write(f"CHAPTER04={get_timestamp(offset_list[2])}\n")
            outfile.write(f"CHAPTER04NAME={ENDING}\n")
            if not snap_end:
                outfile.write(f"CHAPTER05={get_timestamp(offset_list[3])}\n")
                outfile.write(f"CHAPTER05NAME={POST_ED}\n")
        
    outfile.close()
    
def validate_themes(args, t_path):
    if args.no_download:
        valid = False
        if os.path.isdir(t_path):
            for theme_file in os.scandir(t_path):
                if ".ogg" in str(theme_file):
                    valid = True
        if not valid:
            print("No valid themes. Specify a search-name to download themes.", file=sys.stderr)
            sys.exit(1)
        
def try_download(args, t_path):
    if not args.no_download:
        try:
            series_json = get_series_json(args.search_name)
            download_themes(t_path, series_json)
        except:
            print(f"Couldn't access api or download", file=sys.stderr)
            
def match_themes(args, t_path):
    offset_list = []
    for theme_file in os.scandir(t_path): # TODO: More inteligent ordering could save some time
        if ".ogg" in str(theme_file) and len(offset_list) < 4:
            offset1, offset2 = (find_offset(args.input, Path(theme_file.path), t_path, args.charts))
            if offset1 != None:
                offset_list.append(offset1)
                offset_list.append(offset2)
    
    return offset_list
                
def main():
    args = parse_args()
    t_path = os.path.join(args.work_path, ".themes") 
    
    validate_themes(args, t_path)      
    make_folders(args.work_path) 
    try_download(args, t_path)
    offset_list = match_themes(args, t_path)
    
    file_duration = librosa.get_duration(filename=args.input)
    offset_list.sort()
    if chapter_validator(offset_list, file_duration):  
        generate_chapters(offset_list, file_duration, args.output)
    
    if args.delete_themes:
        shutil.rmtree(t_path)

if __name__ == "__main__":
    main()