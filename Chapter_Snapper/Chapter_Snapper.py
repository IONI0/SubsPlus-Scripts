# Chapter Snapper V2.0
import sys
import bisect
import math
import re
import time
import argparse
from pathlib import Path

def parse_srt_time(string):
    hours, minutes, seconds, milliseconds = map(int, re.match(r"(\d+):(\d+):(\d+)\.(\d+)", string).groups())
    return hours * 3600000 + minutes * 60000 + seconds * 1000 + milliseconds 
        
def parse_scxvid_keyframes(text):
    return [i-3 for i,line in enumerate(text.splitlines()) if line and line[0] == 'i']
        
def parse_keyframes(path):
    with open(path) as file_object:
        text = file_object.read()
    if text.find('# XviD 2pass stat file')>=0:
        frames = parse_scxvid_keyframes(text)
    else:
        raise Exception('Unsupported keyframes type')
    if 0 not in frames:
        frames.insert(0, 0)
    return frames
        
class Timecodes(object):
    TIMESTAMP_END = 1
    TIMESTAMP_START = 2

    def __init__(self, times, default_fps):
        super(Timecodes, self).__init__()
        self.times = times
        self.default_frame_duration = 1000.0 / default_fps if default_fps else None

    def get_frame_time(self, number, kind=None):
        if kind == self.TIMESTAMP_START:
            prev = self.get_frame_time(number-1)
            curr = self.get_frame_time(number)
            return prev + int(round((curr - prev) / 2.0))
        elif kind == self.TIMESTAMP_END:
            curr = self.get_frame_time(number)
            after = self.get_frame_time(number+1)
            return curr + int(round((after - curr) / 2.0))

        try:
            return self.times[number]
        except IndexError:
            if not self.default_frame_duration:
                raise ValueError("Cannot calculate frame timestamp without frame duration")
            past_end, last_time = number, 0
            if self.times:
                past_end, last_time = (number - len(self.times) + 1), self.times[-1]

            return int(round(past_end * self.default_frame_duration + last_time))

    def get_frame_number(self, ms, kind=None):
        if kind == self.TIMESTAMP_START:
            return self.get_frame_number(ms - 1) + 1
        elif kind == self.TIMESTAMP_END:
            return self.get_frame_number(ms - 1)

        if self.times and self.times[-1] >= ms:
            return bisect.bisect_left(self.times, ms)

        if not self.default_frame_duration:
            raise ValueError("Cannot calculate frame for this timestamp without frame duration")

        if ms < 0:
            return int(math.floor(ms / self.default_frame_duration))

        last_time = self.times[-1] if self.times else 0
        return int((ms - last_time) / self.default_frame_duration) + len(self.times)

    @classmethod
    def _convert_v1_to_v2(cls, default_fps, overrides):
        # start, end, fps
        overrides = [(int(x[0]), int(x[1]), float(x[2])) for x in overrides]
        if not overrides:
            return []

        fps = [default_fps] * (overrides[-1][1] + 1)
        for start, end, fps in overrides:
            fps[start:end + 1] = [fps] * (end - start + 1)

        v2 = [0]
        for d in (1000.0 / f for f in fps):
            v2.append(v2[-1] + d)
        return v2

    @classmethod
    def parse(cls, text):
        lines = text.splitlines()
        if not lines:
            return []
        first = lines[0].lower().lstrip()
        if first.startswith('# timecode format v2'):
            tcs = [x for x in lines[1:]]
            return Timecodes(tcs, None)
        elif first.startswith('# timecode format v1'):
            default = float(lines[1].lower().replace('assume ', ""))
            overrides = (x.split(',') for x in lines[2:])
            return Timecodes(cls._convert_v1_to_v2(default, overrides), default)
        else:
            raise Exception('This timecodes format is not supported')

    @classmethod
    def from_file(cls, path):
        with open(path) as file:
            return cls.parse(file.read())

    @classmethod
    def cfr(cls, fps):
        return Timecodes([], default_fps=fps)
    
def get_closest_kf(frame, keyframes):
    idx = bisect.bisect_left(keyframes, frame)
    if idx == len(keyframes):
        return keyframes[-1]
    if idx == 0 or keyframes[idx] - frame < frame - (keyframes[idx-1]):
        return keyframes[idx]
    return keyframes[idx-1]
    
def main():
    parser = argparse.ArgumentParser(description="Snap chapters to nearest keyframe.")
    parser.add_argument(
        "--input", "-i", type=Path, required=True,
        help="Chapter file. Must be in simple format.",
    )
    
    parser.add_argument(
        "--keyframes", "-kf", type=Path, required=True,
        help="SCXvid keyframes. Try to have minimal mkv delay or it might not line up.",
    )
    
    parser.add_argument(
        "--output", "-o", type=Path,
        help="Output chapter file. Defaults to where input is.",
    )
    
    parser.add_argument(
        "--snap-ms", "-s", type=int, default=1000,
        help="How many milliseconds to consider snapping to. Defaults to 1000ms.",
    )
    
    parser.add_argument(
        "--fps", type=float, default=23.976,
        help="FPS of the video. Defaults to 23.976.",
    )
    
    args = parser.parse_args()
    chapter_path = args.input
    keyframes_path = args.keyframes
    out_path = args.output
    snap_ms = args.snap_ms
    fps = args.fps
    
    if out_path is None:
        out_path = chapter_path.with_name(chapter_path.stem + "_snapped.txt")
    
    timecodes = Timecodes.cfr(fps)
    keyframes_list = parse_keyframes(keyframes_path)
    
    with open(chapter_path, "r") as chapter_file:
        chapter_read = chapter_file.readlines()
        
    if not chapter_read[0].startswith("CHAPTER01="):
        print("Invalid chapter format.", file=sys.stderr)
        sys.exit(1)
        
    chapter_build = []
    for idx, line in enumerate(chapter_read):
        if idx % 2 == 0:
            chapter_split = line.split("=")
            start_ms = parse_srt_time(chapter_split[1])
            start_frame = timecodes.get_frame_number(start_ms, timecodes.TIMESTAMP_START)
            closest_frame = get_closest_kf(start_frame, keyframes_list)
            closest_time = timecodes.get_frame_time(closest_frame, timecodes.TIMESTAMP_START)
            if abs(closest_time - start_ms) <= snap_ms and start_ms != 0:
                start_ms = max(0, closest_time)
                timesec = start_ms/1000
                timestamp = time.strftime(f"%H:%M:%S.{round(timesec%1*1000):03}", time.gmtime(timesec))
                chapter_build.append(f"{chapter_split[0]}={timestamp}\n")
            else:
                chapter_build.append(line)
        else:
            chapter_build.append(line)
            
    with open(out_path, "w") as out_file:
        out_file.writelines(chapter_build)    
    
if __name__ == '__main__':
    main()