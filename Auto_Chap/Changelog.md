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