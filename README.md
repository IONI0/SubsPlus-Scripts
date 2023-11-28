# SubsPlus+ Automation Scripts

Automation scripts made for fixing Hidive subtitles and other functions.

## Scripts

These are the first batch of scripts. There are a few more I haven't finished cleaning up yet, they might be added later. I'm not very experienced programmer so constructive criticism is appreciated. 

These scripts are first and foremost made for SubsPlus+ releases and Hidive subtitles, don't expect the more specific scripts to work outside of that context.

### Auto_Chap

Generate chapters by matching themes downloaded from [AnimeThemes](https://animethemes.moe) to the episode. It creates a `.themes` folder with the downloaded themes for future runs and charts showing where the themes matched in the episode. Chapters will not be generated if 0 or more than 2 themes are matched, or 2 themes are in the same half of the episode.

#### Dependencies
```
pip install -r requirements.txt
```

#### Usage
```console
$ python Auto_Chap.py --help
usage: Auto_Chap.py [-h] --input INPUT [--search-name SEARCH_NAME] [--work-path WORK_PATH] [--output OUTPUT]
                         [--delete-themes] [--charts]

Automatic anime chapter generator using animethemes.

options:
  -h, --help            show this help message and exit
  --input INPUT, -i INPUT
                        Video/Audio file.
  --search-name SEARCH_NAME, -s SEARCH_NAME
                        Search to pass to animethemes.moe Example: Spy Classroom Season 2. For no theme downloading,
                        don't add this argument.
  --work-path WORK_PATH, -w WORK_PATH
                        Place to create a .themes folder for storing persistant information per series. Defaults to
                        where the episode is.
  --output OUTPUT, -o OUTPUT
                        Output chapter file. Defaults to where the episode is.
  --delete-themes, -d   Delete the themes and charts after running.
  --charts, -c          Make charts of correlation scores. They can almost double processing time in some cases
                        though.
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
Snap chapter file to nearest keyframe. Chapter file must be in simple chapter format.

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

### Overlap_Blue
Change outline color of a line when it is overlapping another. Supports top and bottom track but only if they are defined in styles not inline. Works well for Crunchyroll and Hidive shows.

#### Usage
```
python Overlap_Blue.py infile.ass outfile.ass
```

Change settings at the top of the script. Specify dialogue font if you don't want it to color an alternative dialogue font.
```python
DIALOGUE_FONT = None
COLOR_HEX = "&H743E15&"
```

---

### Hidive_Splitter
Relavant for [multi-downloader-nx](https://github.com/anidl/multi-downloader-nx) and [hidive-downloader-nx](https://github.com/anidl/hidive-downloader-nx). Split and combine lines so that each line has its own event. This prevents subtitles from shifting positions. Note: Some orders will be reversed to preserve rendering position.

#### Usage
```
python Hidive_Splitter.py infile.ass outfile.ass
```

---

### P-Proper_Stutter
Capitalise and fix stutters:
- F-f-find -> F-F-Find
- Sh-she -> Sh-She
- W-when -> Wh-When
- S..So -> S-So or S... So

#### Usage
```
python P-Proper_Stutter.py infile.ass outfile.ass
```

---

### Regex_Stuff
Designed for hidive scripts from [multi-downloader-nx](https://github.com/anidl/multi-downloader-nx).

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

## Acknowledgements
- [Audio Offset](https://github.com/hiisi13/audio-offset-finder) for finding themes within an episode
- [AnimeThemes](https://animethemes.moe) api for getting themes
- [iamevn](https://gist.github.com/iamevn/6d796a1c8296ac325da4545fd20caf2f) ass parsing code
- [tp7/Prass](https://github.com/tp7/Prass) keyframe snapping code for Chapter_Snapper