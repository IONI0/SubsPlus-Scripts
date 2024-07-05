# Auto_Chap Changelog

## V3.0
- Make chapters frame-perfect by using `--snap` to snap them to scene changes within a certain millisecond window. This requires new dependencies [Vapoursynth](https://github.com/vapoursynth/vapoursynth), [ffm2](https://github.com/FFMS/ffms2), and [vapoursynth-scxvid](https://github.com/dubhater/vapoursynth-scxvid). If you are not using this feature then these dependencies do not need to be installed. It efficiently generates needed keyframes and is very fast compared to generating keyframes for the entire episode, taking only about 2 seconds.
- Filter search year of the series using `--year`.
- Filter for series released on or after that year using a negative number after `--year`. I added this because search for multi-season shows can sometimes give you the wrong one.

## V3.1
- Fix for matches right at the beginning of the episode being off by a few seconds. This is quite important as it would sometimes skip the first cut after the OP such as in Apothecary Diaries episode 12.
- Switch to using AnimeThemes' slug for theme names so that stuff like ED-TV for Frieren are now downloaded.
- Added progress indicator messages.
- More error handling for snap.
- Printed snapped times should now be the same as final output chapter times.
- Snap now defaults to 1000ms if no value added.

## V3.2
- Theme downloading now checks all versions of the theme so that stuff like Frieren's cour 2 ED that uses a different part of the same song can now be grabbed.
- Redid progress indicators again with separators and better formatted messages.
- Theme downloader now checks if a theme is actually present in the directory even if data.json says it should be and re-downloads if it is not.

## V3.3
- Updated to work on new animethemes api. Since "updated_at" times are no longer used, data.json now uses the "filename" data for each theme to keep track of if they need updating. This means every series will have to be updated and themes redownloaded to fit the new data.json format.

## V3.4
- Found out how to access "updated_at" again which should mean that it can detect more accurately when a theme has been updated. Updated data.json to store both "updated_at" and the animethemes "filename" but unfortunately this format change means all themes will have to be redownloaded again.

## V4.0
- Up to **2-3x faster theme matching** by using ffmpeg to extract the audio from mkv to a temp file, downsampling the audio, and using 2 threads for matching OP and ED in parallel. Chart creation is also done in parallel on a separate process
    - The downsampling factor defaults to 8 and can be changed using `--downsample 32` for example. There are diminishing returns as you increase it.
    - ffmpeg is required in PATH, it will now create a temp `.autochap.wav` file if the input is an mkv file. The temp file uses the first audio track and may be quite big.
- Up to **2-5x faster theme downloading** by downloading in parallel. Speed up depends on how many themes in the series, internet speeds, etc.
    - Themes to download in parallel defaults to 10 and can be changed using `--parallel-dl 2` for example
- Reduced false positives where only the beginning of a theme is played by using the entire theme audio to match instead of first 30 seconds
- Fixed `--year` to only match that specific year if the number is non-negative

## V4.1
- Up to **2-3x faster theme matching** than V4.0
    - Speed-up applies more when there are more themes that need to be matched. Optimisation includes only loading the episode audio once at the beginning and using the audioread module to load theme files.
- Fixed compatibility issue with macos caused by audioread loading.
- Use `--score` to adjust how lenient the matching should be. Increase from default to reduce false positives. Decrease it to be more lenient. Score is y-axis in charts divided by the downsample factor.
- Increased default score from 2000 to 4000
- Increased default downsample factor from 8 to 32

## V4.1a
- Revert default score from 4000 back to 2000
- Please give me feedback on the change in downsample default. If 32 causes any errors then let me know.

## V4.2
- Fixed non-matches for episodes where themes in the episode are slightly shorter such as when a theme is played at the very end of the episode. Now uses the beginning 90% of the theme for matching. The portion of the theme used can be changed using `--theme-portion`
- Moved episode snap option for snapping chapters to the start and end of the episode to an optional argument using `--episode-snap` The default is still 4 seconds so that previews/endscreens 5 seconds long will get their own chapter.
- Fixed typo in chapter output when there is only an ED.
- Rearranged arguments and fixed typos.
- Trimmed trailing whitespace.
- Standardised error messages.