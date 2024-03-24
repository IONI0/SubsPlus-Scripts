# Auto Chap V3.3
import sys
import json
import os
import urllib
import time
import warnings
import argparse
import shutil
import math
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

# Seconds window to snap chapters to beginning or end of episode
episode_snap_sec = 4 

# Ignore librosa warnings about audioread. Basically this will break with librosa 1.0 when they remove it
warnings.filterwarnings("ignore", category=FutureWarning) 
warnings.filterwarnings("ignore", category=UserWarning)

def parse_args():
    parser = argparse.ArgumentParser(description="Automatic anime chapter generator using AnimeThemes.")
    parser.add_argument(
        "--input", "-i", type=Path, required=True,
        help="Video/Audio file.",
    )
    
    parser.add_argument(
        "--search-name", "-s", type=str,
        help="Search to pass to animethemes.moe Example: Spy Classroom Season 2. To only use themes that are already downloaded, don't add this argument.",
    )
    
    parser.add_argument(
        "--year", type=int,
        help="Release year to help filter the search. Put the negative number to allow that year or later.",
    )
    
    parser.add_argument(
        "--snap", type=int, nargs='?', const=1000, default=None,
        help="Milisecond window to snap to nearest keyframe for frame-perfect chapters. Efficiently generates necessary keyframes from video. Defaults to 1000ms if no value added. Values higher than about 1000 currently crash.",
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
        
    if args.snap is not None:
        if args.snap > 1000:
            print("Snap values higher than about 1000 currently crash SCXvid. Please lower it.", file=sys.stderr)
            sys.exit(1)
        
    return args

def print_seperator():
    print("------------------------------") 

def make_folders(work_path):
    subdirectory_path = work_path / ".themes" / "charts"
    shutil.rmtree(subdirectory_path, ignore_errors=True)
    subdirectory_path.mkdir(parents=True)

def get_series_json(args):
    api_search_call = f"https://api.animethemes.moe/search?fields[search]=anime&q={urllib.parse.quote(args.search_name)}"
    if args.year:
        if args.year < 0:
            api_search_call += f"&filter[year-gte]={abs(args.year)}"
        else:
            api_search_call += f"&filter[year-gte]={args.year}"
    global_search = requests.get(api_search_call).json()
    series_slug = global_search["search"]["anime"][0]["slug"]
    series_json = requests.get(f"https://api.animethemes.moe/anime/{series_slug}?include=animethemes.animethemeentries.videos.audio").json()
    return series_json["anime"]

def download_theme(t_path, theme_name, video_json):
    print(f"{theme_name}: Downloading...", end="", flush=True)
    response = requests.get(video_json["audio"]["link"])
    if response.status_code == 200:
        download_path = f'{t_path}/{theme_name}'
        download_path += ".ogg"
        with open(download_path, "wb") as file:
            file.write(response.content)
        print(f"\r{theme_name}: Downloaded     ", file=sys.stderr)
    else:
        print(f"\rFailed to download {theme_name}. Status code:", response.status_code, file=sys.stderr)

def download_themes(t_path, series_json):
    try:
        with open(os.path.join(t_path, "data.json")) as data:
            stored_data = json.load(data)
    except Exception:
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
        audio_version = 1
        audio_links = [] 
        cur_theme = theme["slug"] # OP1 or ED3, etc.
        if not cur_theme[-1].isdigit():
            cur_theme = cur_theme + "1" 
        for version in theme["animethemeentries"]: # Different video versions of theme
            full_cur_theme = cur_theme
            if audio_version > 1:
                full_cur_theme += f"v{audio_version}"
            for video in version["videos"]:
                if video["overlap"] != "None": # No overs or transitions
                    continue
                try: # Look to see if it is in data.json or needs an update
                    if video["audio"]["filename"] == stored_data[full_cur_theme] and video["audio"]["link"] not in audio_links and \
                        os.path.isfile(os.path.join(t_path, full_cur_theme + ".ogg")):
                            audio_links.append(video["audio"]["link"])
                            print(f"{full_cur_theme}: Found in directory", file=sys.stderr)
                            audio_version += 1
                            break
                except Exception:
                    pass
                stored_data[full_cur_theme] = video["audio"]["filename"] # Add to data.json
                if video["audio"]["link"] not in audio_links:
                    audio_links.append(video["audio"]["link"])
                    download_theme(t_path, full_cur_theme, video)
                    audio_version += 1
                                                     
    with open(os.path.join(t_path, "data.json"), "w") as outfile:
        json.dump(stored_data, outfile, indent=4)     

def generate_chart(theme_name, c, t_path, matched=True):
    try:
        print(f"{theme_name}: Generating chart...", end="", flush=True)
        fig, ax = plt.subplots()
        ax.plot(c)
    except Exception:
        print(f"\r{theme_name}: Could not plot figure         ", file=sys.stderr)
        return
        
    try:
        if matched:
            fig.savefig(os.path.join(f"{t_path}", "charts", f"{theme_name}_matched.png"))
        else:
            fig.savefig(os.path.join(f"{t_path}", "charts", f"{theme_name}.png"))
    except Exception:
        print(f"\r{theme_name}: Could not save figure           ", file=sys.stderr)
        return
    
    print(f"\r{theme_name}: Chart generated           ")

def find_offset(within_file, find_file, t_path, make_charts, window = 30): # Change window size for accuracy
    theme_name = os.path.splitext(find_file.name)[0]
    
    print(f"{theme_name}: Matching...", end="", flush=True)
    
    try:
        y_within, sr_within = librosa.load(within_file, sr=None)
    except Exception:
        print("\nCould not load input file", file=sys.stderr)
        sys.exit(1)
    y_find, _ = librosa.load(find_file, sr=sr_within)
    
    silence = np.zeros(5 * sr_within) # 5 secs silence prepended to fix matches at the beginning of episode
    within_adjust = np.concatenate((silence, y_within))

    try:
        c = signal.correlate(within_adjust, y_find[:sr_within*window], mode="valid", method="fft")
    except Exception:
        print(f"\r{theme_name}: Error in correlate. Continuing...", file=sys.stderr)
        return None, None
    
    required_score = 1000 # To prevent false positives. Number is a bit arbitrary 
    
    match_idx = np.argmax(c) # First one to be over 1000
    score = np.max(c)
    offset = max(round(match_idx / sr_within, 2) - 5, 0)
        
    duration = librosa.get_duration(path=find_file)
    
    if score > required_score: 
        print(f"\r{theme_name}: Matched from {get_timestamp(offset)} -> {get_timestamp(offset + duration)}", file=sys.stderr)
        if make_charts:
            generate_chart(theme_name, c, t_path, True)
        return offset, (offset + duration)
    
    else:
        print(f"\r{theme_name}: Not matched       ", file=sys.stderr)
        if make_charts:
            generate_chart(theme_name, c, t_path, False)
        return None, None
    
def get_timestamp(timesec):
    timestamp = time.strftime(f"%H:%M:%S.{round(timesec%1*1000):03}", time.gmtime(timesec))
    return timestamp

def chapter_validator(offset_list, file_duration):
    if len(offset_list) == 0:
        print_seperator()
        print("No matches", file=sys.stderr)
        return False
    elif len(offset_list) == 2:
        return True
    elif len(offset_list) == 4:
        if offset_list[0] > (file_duration / 2) and offset_list[2] > (file_duration / 2):
            print_seperator()
            print("Chapters not valid. They both start in the second half", file=sys.stderr)
            return False
        elif offset_list[0] < (file_duration / 2) and offset_list[2] < (file_duration / 2):
            print_seperator()
            print("Chapters not valid. They both start in the first half", file=sys.stderr)
            return False
        else:
            return True
    else:
        print_seperator()
        print("Chapters not valid. Invalid number of offsets", file=sys.stderr)
        return False
        
def generate_chapters(offset_list, file_duration, out_path):
    outfile = open(out_path, "w", encoding="utf-8")
    snap_beginning = False
    snap_end = False
    ed_only = False
    
    if offset_list[0] < episode_snap_sec:
        snap_beginning = True
    
    if offset_list[-1] > (file_duration - episode_snap_sec):
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
        print("Searching AnimeThemes...", end="", flush=True)
        try:
            series_json = get_series_json(args)
            print(f'\rAnimeThemes matched series: {series_json["name"]}', file=sys.stderr)
            print_seperator()
            download_themes(t_path, series_json)
            print_seperator()
        except Exception:
            print(f"\rCouldn't access api or download", file=sys.stderr)
            
def match_themes(args, t_path):
    matched_OP = False
    matched_ED = False
    offset_list = []
    for theme_file in os.scandir(t_path): # TODO: More inteligent ordering could save some time
        if ".ogg" in str(theme_file) and len(offset_list) < 4:
            theme_name = os.path.splitext(Path(theme_file.path).name)[0]
            if "OP" in theme_name and matched_OP:
                print(f"{theme_name}: Skipping because already matched an OP", file=sys.stderr)
                continue
            elif "ED" in theme_name and matched_ED:
                print(f"{theme_name}: Skipping because already matched an ED", file=sys.stderr)
                continue
            
            offset1, offset2 = (find_offset(args.input, Path(theme_file.path), t_path, args.charts))
            
            if offset1 != None:
                if "OP" in theme_name:
                    matched_OP = True
                elif "ED" in theme_name:
                    matched_ED = True
                offset_list.append(offset1)
                offset_list.append(offset2)
    
    return offset_list

def time_to_frame(timesec, framerate, floor = True):
    frame = timesec * framerate
    if floor:
        return math.floor(frame)
    else:
        return math.ceil(frame)

def frame_to_time(frame, framerate, floor = True):
    if floor:
        middle_frame = max(0, frame - 0.5)
    else:
        middle_frame = frame + 0.5

    secs = middle_frame / framerate

    return secs

def generate_search_pattern(window):
    result = [window + 1]

    for i in range(1, window + 1):
        result.append(window + 1 - i)
        result.append(window + 1 + i)

    return result

def get_keyframe_frame(frame, snap_window_frames, clip_length, clip, core):
    # Generate the keyframes in range with one more at the beginning since the first is always keyframe
    # Scxvid needs to go sequentially and wwxd is inaccurate in testing
    search_start_frame = max(frame - snap_window_frames - 1, 0)
    search_end_frame = min(frame + snap_window_frames, clip_length) # Should already be one more than the last index
    if search_start_frame >= search_end_frame:
        return
    trimmed_clip = clip[search_start_frame:search_end_frame]
    try:
        scxvid_clip = core.scxvid.Scxvid(trimmed_clip)
    except Exception:
        raise ImportError("You need to install Scxvid in vapoursynth plugins\n"
                          "https://github.com/dubhater/vapoursynth-scxvid")
    
    search_pattern = generate_search_pattern(snap_window_frames)
    for i in search_pattern:
        if i <= 0 or i >= trimmed_clip.num_frames:
            continue
        actual_frame = frame - snap_window_frames - 1 + i
        props = scxvid_clip.get_frame(i).props
        scenechange = props._SceneChangePrev
        if scenechange:
            return actual_frame

def snap(args, offset_list):
    try:
        import vapoursynth as vs
        from vapoursynth import core
    except Exception:
        raise ImportError("You need to install in vapoursynth for snapping\n"
                          "https://github.com/vapoursynth/vapoursynth")
        
    try:
        clip = core.ffms2.Source(source=args.input, cache=False)
    except Exception:
        raise ImportError("Could not load video or you haven't installed ffms2 in vapoursynth plugins for snapping\n"
                          "https://github.com/FFMS/ffms2")
    
    print(f"Snapping chapters...", end="", flush=True)
    
    clip = core.resize.Bilinear(clip, 640, 360, format=vs.YUV420P8)
    
    clip_length = clip.num_frames
    fps = float(clip.fps.numerator) / float(clip.fps.denominator)
    
    snapped_offsets = []
    for offset in offset_list:
        offset_frame =  time_to_frame(offset, fps, floor=False)
        snap_window_frames = round(args.snap / 1000 * fps)
        snap_frame = get_keyframe_frame(offset_frame, snap_window_frames, clip_length, clip, core)
        
        if snap_frame:
            snapped_offsets.append(frame_to_time(snap_frame, fps, floor=True))
        else:
            snapped_offsets.append(offset)
    
    return snapped_offsets

def print_snapped_times(offset_list, file_duration):
    print("\rSnapped times:        ", file=sys.stderr)
    
    # Episode duration snapping
    ep_snapped_offsets = offset_list.copy()
    if ep_snapped_offsets[0] < episode_snap_sec:
        ep_snapped_offsets[0] = 0
    
    if ep_snapped_offsets[-1] > (file_duration - episode_snap_sec):
        ep_snapped_offsets[-1] = file_duration
        
    print(f"{get_timestamp(ep_snapped_offsets[0])} -> {get_timestamp(ep_snapped_offsets[1])}", file=sys.stderr)
    
    if len(ep_snapped_offsets) == 4:
        print(f"{get_timestamp(ep_snapped_offsets[2])} -> {get_timestamp(ep_snapped_offsets[3])}", file=sys.stderr)
            
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
        if args.snap:
            print_seperator()
            offset_list = snap(args, offset_list)
            print_snapped_times(offset_list, file_duration)
        generate_chapters(offset_list, file_duration, args.output)
    
    if args.delete_themes:
        shutil.rmtree(t_path)

if __name__ == "__main__":
    main()