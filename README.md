# SubsPlus+ Automation Scripts
Automation scripts made for fixing Hidive subtitles and other functions.

## Scripts
Check the wiki tab for additional information. I'm not an experienced programmer, so constructive criticism is appreciated.

These scripts are first and foremost made for SubsPlus+ releases and Hidive subtitles, so don't expect the more specific scripts to work outside of that context.

---

### Auto_Chap
Generate chapters by matching themes downloaded from [AnimeThemes](https://animethemes.moe) to the episode.

It creates a `.themes` folder with the downloaded themes for future runs and charts showing where the themes matched in the episode. Chapters will not be generated if no matches or more than 2 themes are matched, or 2 themes are in the same half of the episode. Themes tagged with `Transition` or `Over` on animethemes will not be downloaded and non-conventional themes like Oshi no Ko will likely not work as intended.

Note: You should mux with the outputed chapter file with mkvmerge but if you want to manually input chapters then get them from the output chapter file since the times in the logs are not final.

#### Dependencies
```
pip install -r requirements.txt
```

ffmpeg is required to be installed in PATH.

If you want frame-perfect chapters using `--snap`, keyframe generation requires:
- https://github.com/vapoursynth/vapoursynth
- https://github.com/FFMS/ffms2 (Install in vapoursynth plugins)
- https://github.com/dubhater/vapoursynth-scxvid (Install in vapoursynth plugins)

#### Usage
```console
$ python Auto_Chap.py --help
usage: Auto_Chap.py [-h] --input INPUT [--output OUTPUT] [--search-name SEARCH_NAME] [--year YEAR]
                    [--snap [SNAP]] [--episode-snap EPISODE_SNAP] [--score SCORE]
                    [--theme-portion THEME_PORTION] [--downsample DOWNSAMPLE] [--parallel-dl PARALLEL_DL]
                    [--work-path WORK_PATH] [--delete-themes] [--charts]

Automatic anime chapter generator using AnimeThemes.

options:
  -h, --help            show this help message and exit
  --input INPUT, -i INPUT
                        Video/Audio file.
  --output OUTPUT, -o OUTPUT
                        Output chapter file. Defaults to where the episode is.
  --search-name SEARCH_NAME, -s SEARCH_NAME
                        Search to pass to animethemes.moe Example: Spy Classroom Season 2. To only use
                        themes that are already downloaded, don't add this argument.
  --year YEAR           Release year to help filter the search. Put the negative number to allow that year
                        or later.
  --snap [SNAP]         Millisecond window to snap to nearest keyframe for frame-perfect chapters.
                        Efficiently generates necessary keyframes from video. Defaults to 1000ms if no value
                        added. Values higher than about 1000 currently crash.
  --episode-snap EPISODE_SNAP
                        Window in seconds to snap chapters to the start or end of the episode. This gets
                        applied at the very end. Defaults to 4.
  --score SCORE         Score required for a theme to be accepted as a match. Increase it to reduce false
                        positives, decrease it to be more lenient. Score is y-axis in charts divided by
                        downsample factor. Defaults to 2000.
  --theme-portion THEME_PORTION
                        Portion of a theme required in the episode to be a match. Keep below 1 so that it
                        can still match themes that get slightly cut off. Defaults to 0.9.
  --downsample DOWNSAMPLE
                        Factor to downsample audio when matching, higher means speedier potentially with
                        lower accuracy. Defaults to 32.
  --parallel-dl PARALLEL_DL
                        How many themes to download in parallel. Defaults to 10.
  --work-path WORK_PATH, -w WORK_PATH
                        Place to create a .themes folder for storing persistent information per series.
                        Defaults to where the episode is.
  --delete-themes, -d   Delete the themes and charts after running.
  --charts, -c          Make charts of where themes are matched in the episode. They can almost double
                        processing time in some cases though.
```

#### Examples
Generate chapters for an episode.
```
python Auto_Chap.py -i "Dangers in My Heart - 01.mkv" -s "Dangers in My Heart Season 1"
```

Generate chapters without a persistant `.themes` folder.
```
python Auto_Chap.py -i "Dangers in My Heart - 01.mkv" -s "Dangers in My Heart Season 1" -d
```

Work in a project folder and output to chapter path.
```
python Auto_Chap.py -i "Dangers in My Heart - 01.mkv" -s "Dangers in My Heart Season 1" -w "Projects/DMH" -o "Projects/DMH/Chapters/01.chapter.txt"
```

Run with themes predownloaded (in `.ogg` and in `.themes` folder).
```
python Auto_Chap.py -i "Dangers in My Heart - 01.mkv"
```

Filter search for shows that released on or after 2023.
```
python Auto_Chap.py -i "Shangri-la Frontier - 01.mkv" -s "Shangri-la frontier Season 1" --year -2023
```

Snap to nearest keyframe within 1000ms for frame-perfect chapters. Snap values that are too high don't work for some reason but 1000 should be plenty.
```
python Auto_Chap.py -i "Dangers in My Heart - 01.mkv" -s "Dangers in My Heart Season 1" --snap 1000
```

Chapter names can be changed at the top of the script.
```python
PRE_OP = "Prologue"
OPENING = "Opening"
EPISODE = "Episode"
ENDING = "Ending"
POST_ED = "Epilogue"
```

---

### Chapter_Snapper
Snap chapter file to nearest keyframe using existing scxvid keyframes. Chapter file must be in simple chapter format. Useful if you already have keyframes but if not then use the keyframe generation in Auto_Chap.

#### Usage
```console
$ python Chapter_Snapper.py -h
usage: Chapter_Snapper.py [-h] --input INPUT --keyframes KEYFRAMES [--output OUTPUT] [--snap-ms SNAP_MS]
                               [--fps FPS]

Snap chapters to nearest keyframe.

options:
  -h, --help            show this help message and exit
  --input INPUT, -i INPUT
                        Chapter file. Must be in simple format.
  --keyframes KEYFRAMES, -kf KEYFRAMES
                        SCXvid keyframes. Try to have minimal mkv delay or it might not line up.
  --output OUTPUT, -o OUTPUT
                        Output chapter file. Defaults to where input is.
  --snap-ms SNAP_MS, -s SNAP_MS
                        How many milliseconds to consider snapping to. Defaults to 1000ms.
  --fps FPS             FPS of the video. Defaults to 23.976.
```

#### Examples
Generate with increased snap window.
```
python Chapter_Snapper.py -i "autochap.txt" -kf "keyframes.txt" -s 2000 -o "Project/chapter_snapped.txt"
```

---

### Converter
All the other scripts expect to be run off of the output of this. Detects what the new Hidive Q styles should be (Subtitle, Caption, Song) and restyles them. Song detection is very difficult now, there may be false positives or missed insert-songs so keep an eye on it. You can switch between the advanced song detection method and the restrictive one by commenting the other one out.

#### Dependencies
```
pip install ass
```

#### Usage
Accepts new Erai-raws Hidive scripts (where the styles are all named Q#) and multi-downloader-nx Hidive script using settings `--fontSize 48 --originalFontSize false`
```
python Converter.py infile.ass outfile.ass
```

---

### Overlap_Blue
Change outline color of a line when it is overlapping another. Supports top and bottom track but only if they are defined in styles not inline. Works well for Crunchyroll and Hidive shows.

#### Usage
```
python Overlap_Blue.py infile.ass outfile.ass
```

Change settings at the top of the script. Specify dialogue font if you don't want it to color an alternative dialogue font. CENTISECOND_LENIENCY means don't count as overlap if it is less than _ centiseconds. Any value above 0 has a chance of missing overlaps if the frame advances between the two lines. But some scripts may have two lines within the same frame that get misinterpreted as an overlap if no Leniency given.
```python
DIALOGUE_FONT = "SPOverrideF"
COLOR_HEX = "&H743E15&"
CENTISECOND_LENIENCY = 3
```

---

### Hidive_Splitter
Split and combine lines so that each line has its own event. This prevents subtitles from shifting positions. Note: Some orders will be reversed to preserve rendering position. It can be enabled on [multi-downloader-nx](https://github.com/anidl/multi-downloader-nx) by adding `--combineLines` to the arguments but running this on top of them is still safe.

#### Usage
```
python Hidive_Splitter.py infile.ass outfile.ass
```

---

### P-Proper_Stutter
Capitalize and fix stutters:
- F-f-find -> F-F-Find
- Sh-she -> Sh-She
- W-when -> Wh-When
- S..so -> S..So (Can be configure to be S-So or S... So)

#### Usage
```
python P-Proper_Stutter.py infile.ass outfile.ass
```

---

### Regex_Stuff
- Add fade to song styles
- Fix em-dash
- Fix triple dialogue lines
- !? -> ?!
- Increase layers on non 'caption' styles
- Fix incorrectly styled 'caption's

#### Usage
```
python Regex_Stuff.py infile.ass outfile.ass
```

---

### Resampler
Simple script resampler from 720p to 1080p with rounding. Only works for these simple Hidive subtitles, don't try to use this in other cases.


#### Dependencies
```
pip install ass
```

#### Usage
```
python Resampler.py infile.ass outfile.ass
```

---

### Sign_DeOverlap
Send dialogue to the top if it covers a sign. It approximates the bounding boxes of the dialogue and the signs then compares them. Only works with converted Hidive subtitles, don't try to use this in other cases.

#### Dependencies
```
pip install "pillow>=10.1.0"
```

#### Usage
```
python Sign_DeOverlap.py infile.ass outfile.ass
```

---

### Style_Cleanup
Simplify styles to look nicer internally, does not affect how it renders. Original code and idea from [Animorphs](https://github.com/Animorphs) modified into a standalone script.

#### Usage
```
python Style_Cleanup.py infile.ass outfile.ass
```

---

## Acknowledgements
- [hiisi13/Audio Offset](https://github.com/hiisi13/audio-offset-finder) for finding themes within an episode
- [AnimeThemes](https://animethemes.moe) api for getting themes
- [iamevn](https://gist.github.com/iamevn/6d796a1c8296ac325da4545fd20caf2f) ass parsing code
- [tp7/Prass](https://github.com/tp7/Prass) keyframe snapping code for Chapter_Snapper
- [Myaamori/keyframes.py](https://gist.github.com/Myaamori/dfb0030fd4ee44364ca3b0c2c9c9b4aa) inspiration for auto_chap keyframes generation
- [FichteFoll/snap_scenechanges.py](https://gist.github.com/FichteFoll/9184e0ef75df71d7da184c485caf5266) functions and logic for converting frames to time, etc. in auto_chap snapping
- [Animorphs](https://github.com/Animorphs) original code for Style_Cleanup and general help with other scripts