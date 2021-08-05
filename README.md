<p align="center">
<img src="https://github.com/Sbozzolo/motionpicture/raw/master/logo.png" width="636" height="131">
</p>

[![GPLv3
license](https://img.shields.io/badge/License-GPLv3-blue.svg)](http://perso.crans.org/besson/LICENSE.html)
![Tests and documentation](https://github.com/Sbozzolo/motionpicture/workflows/Tests/badge.svg)
[![codecov](https://codecov.io/gh/Sbozzolo/motionpicture/branch/master/graph/badge.svg?token=z7jvNNdwVS)](https://codecov.io/gh/Sbozzolo/motionpicture)
[![PyPI version](https://badge.fury.io/py/motionpicture.svg)](https://badge.fury.io/py/motionpicture)

# Introduction

`motionpicture` is a Python library to simplify the creation of videos out of
individual frames. With `motionpicture`, you just have to specify how to produce
a generic frame, and the package will do everything else for you. In
`motionpicture`, your code can be configured via command-line or text files:
turning your code into a plug-in for `motionpicture` is trivial, so you will be
able to reuse your code with ease.

# Examples

There are two important ingredients to use `motionpicture`: `mopi`, and a
_movie_ file. `mopi` is a command-line utility that comes when you install this
package. It will be your main interface to `motionpicture` and it has a
comprehensive `--help` function. A movie file is a recipe on how to produce a
generic frame. With few small restrictions, you have full control over this file
(more info in section [Movie files](#movie-files)).

In these examples we are going to use `matplotlib` to do the plotting, but you
are completely free to generate frames with any Python package you wish.

## Unveiling a sine wave

In this example, we show how to use `mopi` to generate the following video.
![sine_wave](https://github.com/Sbozzolo/motionpicture/raw/master/sine_wave.gif)

To produce this video, we need the following movie file.
``` python
import matplotlib.pyplot as plt
import numpy as np

class MOPIMovie:
    def __init__(self, _args):
        self.times = np.linspace(0, 10, 100)
        self.values = np.sin(self.times)

    def get_frames(self):
        # Here we tell motionpicture what we consider a frame
        return range(self.times)

    def make_frame(self, path, frame_number):
        # Here we plot a specific frame
        plt.clf()
        plt.plot(self.times[:frame_number], self.values[:frame_number])
        plt.xlim([0, self.times[-1]])
        plt.ylim([-1, 1])
        plt.savefig(path)
```
Assuming this file is saved in `sin_wave.py`, we run

``` sh
mopi -m sin_wave.py -o frames_dir --parallel
```
This is produce the individual frames in a folder `frames_dir` using all the CPUs
available on your machine. Then, it will glue the frames together in a video
that has the default name of `video.mp4`. If you want to change name, or other
properties (e.g., the fps), you can add options to `mopi`
``` sh
mopi -m sin_wave.py -o frames_dir --parallel --fps 10 --movie-name sin_wave
```
This will produce a `sin_wave.mp4` video with 10 frames per second instead

## Unveiling a sine wave with controllable frequency

Let us continue on the example of the sine wave, and let us assume that we want
to explore different frequencies.

We can edit the previous movie file adding a `mopi_add_custom_options`
function:

``` python
def mopi_add_custom_options(parser):
    """Add command-line options specific to this movie."""
    parser.add_argument(
        "-f",
        "--frequency",
        default=1,
        type=int,
        help="Frequency of the sine wave (default: %(default)s)",
    )
```
Then, we edit the `__init__` function too:
``` python
def __init__(self, args):
    self.times = np.linspace(0, 10, 100)
    self.values = np.sin(args.frequency * self.times)
```
Movie files have to have an `__init__` that takes two arguments. The second
is a `Namespace` that contains all the controllable options. These arguments
can be passed via command-line or configuration file.
``` sh
mopi -m sin_wave.py -o frames_dir --parallel --frequency 3
```
This command will produce the following video.

![sine_wave_fast](https://github.com/Sbozzolo/motionpicture/raw/master/sine_wave_fast.gif)

Alternatively, you can put any of arguments in a config file `conf`, for example:

``` text
outdir: frames_dir
frequency: 3
```
Config files support several syntaxes. Once you have the file, just call
``` sh
mopi sin_wave.py -c conf
```
You can use config files and command-line options at the same time, but in case
of conflict, the command-line arguments have the precedence.

## Unveiling data in an arbitrary file

Now that you have seen that you can control movies via command-line, it is time
to introduce you to the plugin system in `motionpicture`.

Suppose we have two-column files with time series data, we can modify the movie
file used in the previous example to animate those files, specifying which one
at run-time.

``` python
def mopi_add_custom_options(parser):
    """Add command-line options specific to this movie."""
    parser.add_argument(
        "-f",
        "--file",
        required=True,
        help="File to plot",
    )
```
Then, we `import numpy as np` and edit the `__init__` function too:
``` python
def __init__(self, args):
    self.times, self.values = np.loadtxt(args.file).T
    self.y_min, self.y_max = np.amin(self.value), np.amax(self.value)
```
We computed the minimum and maximum of the value so that we can adjust the y axis
range. The  `make_frame` method will be the same, with the exception that we change
the `plt.ylim([-1, 1])` line to `plt.ylim([self.y_min, self.y_max])`.

We can save this file as `plot_timeseries` and call `mopi`:
``` sh
mopi -m plot_timeseries -o frames -f my_file.dat
```
Of course, we can add as many options as we wish to control the output. For instance,
we may want to add a switch to use logarithmic axes instead. The class
`MOPIMovie` has full access to the user-supplied options, so you can do anything
you wish.

We did not hard-code anything in `plot_timeseries`, so the code will work for
any dataset. However, if we want to use this file again, but in a different
folder, we would have to copy it over, since `mopi -m` expects the path of the
movie file. Alternatively, we can copy `plot_timeseries` to a specific folder
of our choice, for example `~/.mopi_videos`. Then, we can set the environment
variable `MOPI_MOVIES_DIR` to be `~/.mopi_videos`, and `mopi` will be able to
find `plot_timeseries` from anywhere in your filesystem. In this case, you can
simply call:
``` sh
mopi plot_timeseries -o frames -f my_other_file.dat
```
Essentially, `plot_timeseries` became a plugin for `motionpicture` and you can
animate any data without having to write new code. This is one of the greatest
strengths of `motionpicture`, as it encourages you to write generic code that you
can easily reuse.

# Installation

`motionpicture` is available on PyPI. You can install it with `pip`:

``` sh
pip3 install motionpicture
```

To produce the final video, you have to have `ffmpeg` installed. Without
`ffmpeg`, you will not be able to glue together the frames, but you can still
use `motionpicture` to render the frames.

# Movie files

In the language of `motionpicture`, a movie file is a recipe on how to
generate an individual frame. It is completely up to you how you do that, but
`motionpicture` imposes some minimum requirements:

- It has to be a valid Python 3 file.
- It has to contain a class `MOPIMovie` with a method `make_frame` and a method
  `get_frames`.
- The method `__init__` has to take two arguments.
- The method `get_frames` has to return an iterable (e.g., a list) that
  identifies each frame. The elements of this iterable are passed as the `frame`
  argument to `make_frame`.
- The method `make_frame` has to take two arguments, the `path` of the output of
  the frame, and `frame`, the value that identifies frame (typically the frame
  number). `path` is where the image has to be saved. You are in charge of
  saving the image using the save method of your plotting package.

Other than these requirements, you can do anything you want in the movie file
(e.g., you can add more methods, functions, classes...).

To have support for the `--overwrite` option, the function `make_frame` must
always write the data regardless of possible pre-existing files at destination.

> :warning: Due to its own nature, `motionpicture` has to execute any code that
>           you supply. Do not use `motionpicture` with codes you do not trust!

# `mopi`

`mopi` is a command-line utility with several options. Its `--help` flag can
tell you what it can do:
``` text
General options:
  movie                 Movie to render among the ones found in MOPI_MOVIES_DIR. See bottom of the help message for list.
  -m MOVIE_FILE, --movie-file MOVIE_FILE
                        Path of the movie file.
  -c CONFIG, --config CONFIG
                        Config file path
  --movies-dir MOVIES_DIR
                        Folder where to look form movies.   [env var: MOPI_MOVIES_DIR]
  -o OUTDIR, --outdir OUTDIR
                        Output directory for frames and video.
  --snapshot SNAPSHOT   Only produce the specified snapshot (useful for testing).
  --overwrite           Overwrite files that already exist.
  --disable-progress-bar
                        Do not display the progress bar when generating frames.
  --parallel            Render frames in parallel.
  --skip-existing       Do not generate frames that already exist. No consistency checks are performed.
  --num-workers NUM_WORKERS
                        Number of cores to use (default: 8).
  --max-tasks-per-child MAX_TASKS_PER_CHILD
                        How many chunks does a worker have to process before it is respawned? Higher number typically leads to higher performance
                        and higher memory usage. (default: 1).
  --chunks-size CHUNKS_SIZE
                        How many frames does a worker have to do each time? Higher number typically leads to higher performance and higher memory usage.
  --only-render-movie   Do not generate frames but only render the final video.
  --frame-name-format FRAME_NAME_FORMAT
                        If only-render-movie is set, use this C-style frame name format instead of computing it. For example, '%04d.png' will
                        assemble a video with frames with names 0000.png, 0001.png, and so on, as found in the outdir folder.
  -v, --verbose         Enable verbose output.
  -h, --help            Show this help message and exit.

Frame selection:
  --min-frame MIN_FRAME
                        Do not render frames before this one.
  --max-frame MAX_FRAME
                        Do not render frames after this one.
  --frames-every FRAMES_EVERY
                        Render a frame every N (default: render all the possible frames).

Video rendering options:
  --movie-name MOVIE_NAME
                        Name of output video file, without extension (default: video).
  --extension EXTENSION
                        File extension of the video (default: mp4).
  --fps FPS             Frames-per-second of the video (default: 25).
  --codec CODEC         Codec to use for the final encoding. If not specified, it is determined from the file extension.
  --author AUTHOR       Author metadata in the final video.
  --title TITLE         Title metadata in the final video.
  --comment COMMENT     Comment metadata in the final video.

No movies found in the MOPI_MOVIES_DIR (.)
```

A useful option for debugging is `--snapshot`. If you pass the keyword
`--snapshot` and the identifier for a specific frame (an element of the iterable
`MOPIMoive.get_frames()`), `mopi` will only render that single frame. This
can be used to test your movie file.

Another interesting option is `--only-render-movie`. This skips the generation
of frames and only produces the final video. When this option is enable, `mopi`
will still go through the selection of frames from the movie file, so options
like `--min-frame` or `--frames-every` will affect the result. If you specify
also `--frame-name-format`, you can skip this step too (which skips the movie
file entirely), and just render the final video. This option requires a C-style
format string to specify which files have to be assembled to the final video.
This refers to the name of the files in the output folder.

# Development

We use:
* [Poetry](python-poetry.org) to manage dependencies, build, and publish
  `motionpicture`.
* [Black](https://github.com/psf/black) for formatting the code (with 89
  columns).
* [pytest](https://pytest.org) for unit tests (with `pytest-cov` for test
  coverage).
* GitHub actions for continuous integration.

We are happy to accept contributions.

## A note on the inner workings

Multiprocessing with Python is a pain. Hence, we need to hack our way lo support
parallelism in such a way that is completely transparent to the user. To achieve
this `motionpicture` uses two tricks:
- The movie file is evaluated verbatim with `exec` in the global namespace
- The `MOPIMovie` class is patched to a `pMOPIMovie` (always using `exec`) to
  provide a function `p_make_frames` that works better with `multiprocessing`.

So, `motionpicture` directly manipulates the global namespace to be able to
use multiple processes. This can lead to surprises in the code, for example,
`MOPIMovie` is used without apparently being imported.

# Changelog

See [NEWS.md](https://github.com/Sbozzolo/motionpicture/blob/master/NEWS.md) for
a changelog.

# Credits

The idea for `motionpicture` originated from the `SimVideo` package developed by
Wolfgang Kastaun.

