# Changelog

## Version 0.3.2 (13 April 2023)

Bug fixes:
- Improve compatibility with newer versions of Python

## Version 0.3.1 (6 July 2022)

Bug fixes:
- Check if movie files are Python files using the MIME type provided by libmagic

Other improvements:
- Recommend `--verbose` to see details of traceback

## Version 0.3.0 (29 April 2022)

New features added:
- `--codec`
- `--overwrite` (movie files have to implement this separately)
- `--skip-existing`

- `--maxtasksperchild`
- `--chunksize`

Other improvements:
- `mp4` files are better encoded and should be playable on more devices
- When `verbose`, now `ffmpeg` displays its messages
- Reworked parallelization scheme, now it is more efficient and less memory
  intensive.

Bug fixes:
- Do not require movie file when `--only-render-movie` and `--frame-name-format`
  are passed.

The minimum version of Python required is now Python 3.6.2.

## Version 0.2.0 (5 April 2021)

New features added:
- `--snapshot`
- `--frame-min`, `--frame-max`, `--frames-every`
- `--only-render-movie`, `--frame-name-format`

Other improvements:
- Now, `--verbose` prints more informative error messages, including the ones
  produced by `ffmpeg`

Bug fixes:
- The `--fps` flag now works as intended

## Version 0.1.2 (1 January 2021)

Initial release

