# Changelog

## Version 0.3.0 (Under development)

New features added:
- `--codec`
- `--overwrite` (movie files have to implement this separately)
- `--skip-existing`

Other improvements:
- `mp4` files are better encoded and should be playable on more devices
- When `verbose`, now `ffmpeg` displays its messages

Bug fixes:
- Do not require movie file when `--only-render-movie` and `--frame-name-format`
  are passed.

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

