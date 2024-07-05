# Auto Chap V4.2
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
import subprocess
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import librosa
import audioread.ffdec
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt

### Chapter Names
PRE_OP = "Prologue"
OPENING = "Opening"
EPISODE = "Episode"
ENDING = "Ending"
POST_ED = "Epilogue"

# Ignore librosa warnings about audioread. Try downgrading to librosa < 1.0 if it fully breaks
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

def parse_args():
    parser = argparse.ArgumentParser(description="Automatic anime chapter generator using AnimeThemes.")
    parser.add_argument(
        "--input", "-i", type=Path, required=True,
        help="Video/Audio file.",
    )

    parser.add_argument(
        "--output", "-o", type=Path,
        help="Output chapter file. Defaults to where the episode is.",
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
        help="Millisecond window to snap to nearest keyframe for frame-perfect chapters. Efficiently generates necessary keyframes from video. Defaults to 1000ms if no value added. Values higher than about 1000 currently crash.",
    )

    parser.add_argument(
        "--episode-snap", type=float, default=4,
        help="Window in seconds to snap chapters to the start or end of the episode. This gets applied at the very end. Defaults to 4."
    )

    parser.add_argument(
        "--score", type=int, default=2000,
        help="Score required for a theme to be accepted as a match. Increase it to reduce false positives, decrease it to be more lenient. Score is y-axis in charts divided by downsample factor. Defaults to 2000.",
    )

    parser.add_argument(
        "--theme-portion", type=float, default=0.9,
        help="Portion of a theme required in the episode to be a match. Keep below 1 so that it can still match themes that get slightly cut off. Defaults to 0.9."
    )

    parser.add_argument(
        "--downsample", type=int, default=32,
        help="Factor to downsample audio when matching, higher means speedier potentially with lower accuracy. Defaults to 32.",
    )

    parser.add_argument(
        "--parallel-dl", type=int, default=10,
        help="How many themes to download in parallel. Defaults to 10.",
    )

    parser.add_argument(
        "--work-path", "-w", type=Path,
        help="Place to create a .themes folder for storing persistent information per series. Defaults to where the episode is.",
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

    if args.theme_portion <= 0:
        print("Theme portion must be more than 0.", file=sys.stderr)
        sys.exit(1)
    elif args.theme_portion > 1:
        print("Theme portion must be less than or equal to 1.", file=sys.stderr)
        sys.exit(1)

    args.episode_audio_path = None

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
            api_search_call += f"&filter[year]={args.year}"
    global_search = requests.get(api_search_call).json()
    series_slug = global_search["search"]["anime"][0]["slug"]
    series_json = requests.get(f"https://api.animethemes.moe/anime/{series_slug}?include=animethemes.animethemeentries.videos.audio&fields[audio]=filename,updated_at,link").json()
    return series_json["anime"]

def download_theme(t_path, theme_name, url):
    response = requests.get(url)
    if response.status_code == 200:
        download_path = f'{t_path}/{theme_name}'
        download_path += ".ogg"
        with open(download_path, "wb") as file:
            file.write(response.content)
        print(f"{theme_name}: Downloaded     ", file=sys.stderr)
    else:
        print(f"Failed to download {theme_name}. Status code:", response.status_code, file=sys.stderr)

def download_themes(t_path, args, series_json):
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

    need_download = []

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
                    if video["audio"]["updated_at"] == stored_data[full_cur_theme]["updated_at"] and \
                        video["audio"]["link"] not in audio_links and \
                        os.path.isfile(os.path.join(t_path, full_cur_theme + ".ogg")):
                            audio_links.append(video["audio"]["link"])
                            print(f"{full_cur_theme}: Found in directory", file=sys.stderr)
                            audio_version += 1
                            break
                except Exception:
                    pass
                # Add to data.json
                stored_data[full_cur_theme] = {}
                stored_data[full_cur_theme]["updated_at"] = video["audio"]["updated_at"]
                stored_data[full_cur_theme]["animethemes_filename"] = video["audio"]["filename"]
                if video["audio"]["link"] not in audio_links:
                    need_download.append((full_cur_theme, video["audio"]["link"]))
                    audio_links.append(video["audio"]["link"])
                    audio_version += 1

    if len(need_download) > 0:
        print("Downloading themes...")

    with ThreadPoolExecutor(max_workers=args.parallel_dl) as executor:
        future_to_url = {executor.submit(download_theme, t_path, theme, url): (theme, url) for (theme, url) in need_download}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
            except Exception as exc:
                print(f"{url} generated an exception: {exc}", file=sys.stderr)

    with open(os.path.join(t_path, "data.json"), "w") as outfile:
        json.dump(stored_data, outfile, indent=4)

def generate_chart(theme_name, c, t_path, matched=True):
    try:
        fig, ax = plt.subplots()
        ax.plot(c)
    except Exception as exc:
        print(f"{theme_name}: Could not plot figure - {exc}", file=sys.stderr)
        return

    try:
        if matched:
            fig.savefig(os.path.join(f"{t_path}", "charts", f"{theme_name}_matched.png"))
        else:
            fig.savefig(os.path.join(f"{t_path}", "charts", f"{theme_name}.png"))
    except Exception as exc:
        print(f"{theme_name}: Could not save figure - {exc}", file=sys.stderr)
        return

    print(f"{theme_name}: Chart generated")

def find_offset(y_episode, sr_episode, theme_file, t_path, args):
    theme_name = os.path.splitext(theme_file.name)[0]

    try:
        aro = audioread.ffdec.FFmpegAudioFile(str(theme_file))
        y_theme, _ = librosa.load(aro, sr=sr_episode)
    except Exception as exc:
        print(f"{theme_name}: Could not load theme file - {exc}", file=sys.stderr)
        sys.exit(1)

    y_episode= y_episode[::args.downsample]
    y_theme = y_theme[::args.downsample]

    # 5 secs silence prepended to fix matches at the beginning of episode
    silence_length = int(5 * sr_episode / args.downsample)
    y_episode_adjust = np.empty(silence_length + len(y_episode), dtype=y_episode.dtype)
    y_episode_adjust[:silence_length] = 0
    y_episode_adjust[silence_length:] = y_episode

    duration = librosa.get_duration(path=str(theme_file))
    y_theme_first_portion = y_theme[:int(sr_episode * ((duration + 5) * args.theme_portion) / args.downsample)]

    try:
        c = signal.correlate(y_episode_adjust, y_theme_first_portion, mode="valid", method="auto")
    except Exception as exc:
        print(f"{theme_name}: Error in correlate - {exc}", file=sys.stderr)
        return None, None

    required_score = args.score / args.downsample

    match_idx = np.argmax(c)
    score = np.max(c)
    offset = max(round((match_idx - silence_length) / (sr_episode / args.downsample), 2), 0)

    if score > required_score:
        print(f"{theme_name}: Matched from {get_timestamp(offset)} -> {get_timestamp(offset + duration)}", file=sys.stderr)
        if args.charts:
            with ProcessPoolExecutor() as executor:
                executor.submit(generate_chart, theme_name, c, t_path, True)
        return offset, (offset + duration)

    else:
        print(f"{theme_name}: Not matched", file=sys.stderr)
        if args.charts:
            with ProcessPoolExecutor() as executor:
                executor.submit(generate_chart, theme_name, c, t_path, False)
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

def generate_chapters(offset_list, file_duration, args):
    outfile = open(args.output, "w", encoding="utf-8")
    snap_beginning = False
    snap_end = False
    ed_only = False

    if offset_list[0] < args.episode_snap:
        snap_beginning = True

    if offset_list[-1] > (file_duration - args.episode_snap):
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
        outfile.write(f"CHAPTER02NAME={ENDING}\n")
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
            download_themes(t_path, args, series_json)
            print_seperator()
        except Exception as exc:
            print(f"\rCouldn't access api or download: {exc}", file=sys.stderr)

def extract_episode_audio(args):
    file_path = args.input

    extract_path = f"{str(file_path)}.autochap.wav"
    try:
        os.remove(extract_path)
    except OSError:
        pass

    if str(file_path).endswith(".mkv"):
        print("Extracting episode audio...", end="", flush=True)
        # Extract as a temp wav file
        output = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-i",
                                 file_path, "-map", "0:a:0", extract_path], capture_output=True)
        if len(output.stderr) > 0:
            print("\rextraction error          ", file=sys.stderr)
            print(output.stderr.decode())
            sys.exit(1)

        args.episode_audio_path = extract_path
        print("\rExtracted episode audio      ")
    else:
        args.episode_audio_path = str(args.input)

def process_themes(t_path, args, theme_files, theme_type, y_episode, sr_episode):
        matched_flag = False
        local_offset_list = []
        for (theme_name, theme_path) in theme_files:
            if theme_type in theme_name and matched_flag:
                print(f"{theme_name}: Skipping because already matched an {theme_type}", file=sys.stderr)
                continue
            offset1, offset2 = find_offset(y_episode, sr_episode, theme_path, t_path, args)
            if offset1 is not None:
                matched_flag = True
                local_offset_list.append(offset1)
                local_offset_list.append(offset2)

        return local_offset_list

def match_themes(args, t_path):
    op_files = []
    ed_files = []
    for theme_file in os.scandir(t_path):
        if ".ogg" in str(theme_file):
            theme_name = os.path.splitext(Path(theme_file.path).name)[0]
            theme_path = Path(theme_file.path)
            if "OP" in theme_name:
                op_files.append((theme_name, theme_path))
            elif "ED" in theme_name:
                ed_files.append((theme_name, theme_path))

    offset_list = []
    print("Matching themes...")

    try:
        y_episode, sr_episode = librosa.load(str(args.episode_audio_path), sr=None)
    except Exception as exc:
        print(f"Could not load input file - {str(args.episode_audio_path)}: {exc}", file=sys.stderr)
        sys.exit(1)

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_op = executor.submit(process_themes, t_path, args, op_files, "OP", y_episode, sr_episode)
        future_ed = executor.submit(process_themes, t_path, args, ed_files, "ED", y_episode, sr_episode)

        for future in as_completed([future_op, future_ed]):
            offset_list.extend(future.result())

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

def print_snapped_times(offset_list, file_duration, args):
    print("\rSnapped times:        ", file=sys.stderr)

    # Episode duration snapping
    ep_snapped_offsets = offset_list.copy()
    if ep_snapped_offsets[0] < args.episode_snap:
        ep_snapped_offsets[0] = 0

    if ep_snapped_offsets[-1] > (file_duration - args.episode_snap):
        ep_snapped_offsets[-1] = file_duration

    print(f"{get_timestamp(ep_snapped_offsets[0])} -> {get_timestamp(ep_snapped_offsets[1])}", file=sys.stderr)

    if len(ep_snapped_offsets) == 4:
        print(f"{get_timestamp(ep_snapped_offsets[2])} -> {get_timestamp(ep_snapped_offsets[3])}", file=sys.stderr)

def main():
    args = parse_args()
    t_path = os.path.join(args.work_path, ".themes")

    try:
        validate_themes(args, t_path)
        make_folders(args.work_path)
        try_download(args, t_path)
        extract_episode_audio(args)
        offset_list = match_themes(args, t_path)

        file_duration = librosa.get_duration(path=str(args.episode_audio_path))

        offset_list.sort()
        if chapter_validator(offset_list, file_duration):
            if args.snap:
                print_seperator()
                offset_list = snap(args, offset_list)
                print_snapped_times(offset_list, file_duration, args)
            generate_chapters(offset_list, file_duration, args)
    finally:
        if args.delete_themes:
            shutil.rmtree(t_path)
        try:
            if args.episode_audio_path.endswith(".autochap.wav"):
                os.remove(args.episode_audio_path)
        except Exception:
            pass

if __name__ == "__main__":
    main()