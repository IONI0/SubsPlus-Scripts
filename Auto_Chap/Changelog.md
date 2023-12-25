# Auto_Chap Changelog

## V3.0
- Snap chapters to nearest keyframe, making them frame-perfect by using `--snap`. This requires new dependencies [Vapoursynth](https://github.com/vapoursynth/vapoursynth), [ffm2](https://github.com/FFMS/ffms2), and [vapoursynth-scxvid](https://github.com/dubhater/vapoursynth-scxvid). If you are not using this feature then these dependencies do not need to be installed. It efficiently generated needed keyframes and is very fast compared to generating keyframes for the entire episode taking only about 2 seconds. 
- Filter search year of the series using `--year`.
- Filter for series released on or after that year using a negative number after `--year`. I added this because search for something multi-season shows can sometimes give you the wrong one.

## V3.1
- Fix for matches right at the beginning of the episode being off by a few seconds. This is quite important as it would some times skip the first cut after the OP such as in Apothecary Diaries episode 12.
- Switch to using the slug for theme names so that stuff like ED-TV for Frieren are now downloaded.
- Added progress indicator messages.
- More error handling for snap.
- Printed snapped times should now be the same as final output chapter times.
- Snap now defaults to 1000ms if no value added.