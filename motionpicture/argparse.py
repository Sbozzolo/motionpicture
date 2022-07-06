#!/usr/bin/env python3

# Copyright (C) 2020-2021 Gabriele Bozzola
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, see <https://www.gnu.org/licenses/>.

"""In this module we have all the functions that have to do with dealing with
user-supplied arguments and finding the movie file.

The main function is :py:func:`~.get_args_movie`. This is function does all the
processing of the arguments, and imports the movie file. This function has the
non-trivial task of updating the argument list dynamically, depending on the
user-supplied options. For example, if a movie add custom command-line options, we must
display them in the help message.

A second function is :py:func:`~._init_argparse`. This function defines all the arguments
that can be customized via command-line. If you want to add new arguments, you have to
add them here. Notice, we do not use Python's argparse, but we use ``configargparse``.
This gives the user more flexibility on how to pass the arguments. Since there are tens
of options, users may want to have config files. Also, with ``configargparse`` some
options can be specified with a environment variable, which is nice for options like the
directory where to look for movies.

We also have :py:func:`~._is_movie_file`. This function parses a Python file and checks
if the requirements to be a "movie file" are met. These include containing a
``MOPIMovie`` class with specific methods. If new requirements arise, this function must
be edited.

The function :py:func:`~._check_args` checks the command-line arguments for possible
problems. It is wise to review this function if new options are added.

"""

import ast
import os
import sys
import warnings
from argparse import RawTextHelpFormatter

import configargparse
import magic


def _init_argparse(*args, **kwargs):
    """Initialize a new argparse parser and fill it with arguments.

    If you want to add new command-line options, here is where you have to look
    at.

    The arguments passed to this function and passed to the constructor of
    ``ArgParser``.

    All the arguments will be passed to the ``MOPIMovie`` class.

    :returns: Argparse parser with all the options except the custom ones added
              by the specific movie.
    :rtype: ``configargparse.ArgumentParser``

    """

    parser = configargparse.ArgParser(*args, **kwargs)

    general_options = parser.add_argument_group("General options")

    general_options.add(
        "movie",
        nargs="?",
        help="Movie to render among the ones found in MOPI_MOVIES_DIR. "
        "See bottom of the help message for list.",
    )
    general_options.add_argument("-m", "--movie-file", help="Path of the movie file.")
    general_options.add("-c", "--config", is_config_file=True, help="Config file path")
    general_options.add(
        "--movies-dir",
        default=".",
        help="Folder where to look form movies.",
        env_var="MOPI_MOVIES_DIR",
    )
    general_options.add_argument(
        "-o",
        "--outdir",
        default=".",
        help="Output directory for frames and video.",
    )
    general_options.add(
        "--snapshot",
        help="Only produce the specified snapshot (useful for testing).",
    )
    general_options.add(
        "--overwrite",
        action="store_true",
        help="Overwrite files that already exist.",
    )
    general_options.add(
        "--disable-progress-bar",
        action="store_true",
        help="Do not display the progress bar when generating frames.",
    )
    general_options.add(
        "--parallel", help="Render frames in parallel.", action="store_true"
    )
    general_options.add(
        "--skip-existing",
        help=(
            "Do not generate frames that already exist. "
            "No consistency checks are performed."
        ),
        action="store_true",
    )
    general_options.add(
        "--num-workers",
        default=os.cpu_count(),
        type=int,
        help="Number of cores to use (default: %(default)s).",
    )
    general_options.add(
        "--max-tasks-per-child",
        default=1,
        type=int,
        help="How many chunks does a worker have to process before it is"
        " respawned? Higher number typically leads to higher"
        " performance and higher memory usage. (default: %(default)s).",
    )
    general_options.add(
        "--chunk-size",
        default=1,
        type=int,
        help="How many frames does a worker have to do each time? Higher number"
        " typically leads to higher performance and higher memory usage.",
    )
    general_options.add(
        "--only-render-movie",
        help="Do not generate frames but only render the final video.",
        action="store_true",
    )
    general_options.add(
        "--frame-name-format",
        help="If only-render-movie is set, use this C-style frame name format"
        " instead of computing it. For example, '%%04d.png' will assemble a "
        "video with frames with names 0000.png, 0001.png, and so on, as found"
        " in the outdir folder.",
    )
    general_options.add(
        "-v", "--verbose", help="Enable verbose output.", action="store_true"
    )
    general_options.add_argument(
        "-h",
        "--help",
        action="store_true",
        help="Show this help message and exit.",
    )

    frames_options = parser.add_argument_group("Frame selection")

    frames_options.add_argument(
        "--min-frame",
        help="Do not render frames before this one.",
    )
    frames_options.add_argument(
        "--max-frame",
        help="Do not render frames after this one.",
    )
    frames_options.add_argument(
        "--frames-every",
        default="1",
        type=int,
        help="Render a frame every N (default: render all the possible frames).",
    )

    video_options = parser.add_argument_group("Video rendering options")

    video_options.add_argument(
        "--movie-name",
        default="video",
        help="Name of output video file, without extension (default: %(default)s).",
    )
    video_options.add_argument(
        "--extension",
        default="mp4",
        help="File extension of the video (default: %(default)s).",
    )
    video_options.add_argument(
        "--fps",
        default="25",
        type=int,
        help="Frames-per-second of the video (default: %(default)s).",
    )
    video_options.add_argument(
        "--codec",
        help="Codec to use for the final encoding."
        " If not specified, it is determined from the file extension.",
    )
    video_options.add_argument("--author", help="Author metadata in the final video.")
    video_options.add_argument("--title", help="Title metadata in the final video.")
    video_options.add_argument("--comment", help="Comment metadata in the final video.")
    # If you add new metadata, you have to update the function
    # _metadata_from_args in moviemaker.py

    return parser


def _is_movie_file(path):
    """Check if the file path fulfills the minimum requirement to be used by
    ``motionpicture``.

    These are:
    - It must contain a class ``MOPIMovie``,
    - The class ``MOPIMovie`` must have a method ``__init__`` which has to take
      exactly one argument.
    - The class ``MOPIMovie`` must have a method ``self.get_frames``,
    - The class ``MOPIMovie`` must have a method ``self.make_frame`` which has
      to take exactly two arguments

    To do this, we open the file and inspect the content with ``ast``.

    If new requirement arise, you have to add them here!

    :param path: Path of the file to inspect.
    :type path: str

    :returns: Return True if all the requirements are met, False if at least one
              is not. Along with this, return a string with the description of
              the requirement that was not met (if all are met, the string will be
              empty).
    :rtype: tuple with bool and string

    """
    # We assume that path has been checked somewhere else.
    type_ = magic.from_file(path)
    if not type_.startswith("Python"):
        return (
            False,
            f"File {path} is not a Python file, type: {type_}",
        )

    # First, we check if the file is Python file
    try:
        tree = ast.parse(open(path).read())
    except (SyntaxError, UnicodeDecodeError):
        return False, f"File {path} is not a valid Python file"

    # We check if there is a class ``MOPIMovie``.

    classes_in_tree = {node for node in tree.body if isinstance(node, ast.ClassDef)}

    movies = [class_ for class_ in classes_in_tree if class_.name == "MOPIMovie"]

    if len(movies) == 0:
        return False, f"File {path} does not contain a MOPIMovie class"

    # There must be one movie.
    movie_class = movies[0]

    methods_in_movie = {
        node for node in movie_class.body if isinstance(node, ast.FunctionDef)
    }

    init_method = [method for method in methods_in_movie if method.name == "__init__"]

    if len(init_method) == 0:
        return (
            False,
            f"MOPIMovie class in file {path} does not contain a method __init__",
        )

    num_args_init = len(init_method[0].args.args)
    if num_args_init != 2:
        return (
            False,
            f"__init__ in MOPIMovie class in file {path} takes {num_args_init} arguments, "
            "it should take 2 (self, args)",
        )

    get_frames_method = [
        method for method in methods_in_movie if method.name == "get_frames"
    ]

    if len(get_frames_method) == 0:
        return (
            False,
            f"MOPIMovie class in file {path} does not contain a method get_frames",
        )

    make_frame_method = [
        method for method in methods_in_movie if method.name == "make_frame"
    ]

    if len(make_frame_method) == 0:
        return (
            False,
            f"MOPIMovie class in file {path} does not contain a method make_frame",
        )

    # There must be one make_frame.
    # It has to have exactly two arguments
    num_args = len(make_frame_method[0].args.args)
    if num_args != 3:
        return (
            False,
            f"make_framke in MOPIMovie class in file {path} takes {num_args} arguments, "
            "it should take 3 (self, path, frame_number)",
        )

    return True, ""


def _search_for_movies(folder):
    """Search in the given ``folder`` for files that satisfy the requirement
    specified by the function :py:func:`~._is_movie_file`.

    :param folder: Folder to scan.
    :type folder: str

    :returns: Set of files that contain movies.
    :rtype: set
    """
    files_in_folder = {
        file_
        for file_ in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, file_))
    }
    return {
        file_
        for file_ in files_in_folder
        if _is_movie_file(os.path.join(folder, file_))[0]
    }


def _check_args(args):
    """Check if there are problems with the provided arguments.

    We check:
    - If the number of workers is larger than the number of CPUs.

    :param args: Arguments to check.
    :returns: Arguments as read from command line or from args
    :rtype: ``argparse.Namespace``

    """

    if args.num_workers > os.cpu_count():
        warnings.warn(
            f"You requested {args.num_workers} cores, "
            f"but the machine only has {os.cpu_count()}. "
            "This may result in performance loss."
        )


def get_args_movie(namespace, cli_args=None):
    """Process arguments and import `MOPIMovie` into `namespace``.

    When executing this function, you are also going to execute the movie file.

    This function calls :py:func:`~._init_argparse` to setup the options
    and :py:func:`~._check_args` to check for problems.

    :param namespace: Namespace in which to execute the movie file.
    :type namespace: dict

    :param args: List of arguments as if they were passed via command-line.
                 This is used only for testing.
    :type args: list

    :returns: Arguments as read from command line or from ``args``.
    :rtype: ``argparse.Namespace``

    """

    if cli_args is None:
        # Remove the name of the program from the list of arguments
        cli_args = sys.argv[1:]

    # We do a two-step parsing of the command-line arguments. With the first step,
    # we:
    # 1. Understand if a movie was selected
    # 2. Check what movies are available in the MOPI_MOVIES_DIR
    # 3. Update the help message adding choices for the possible movies.
    #
    # With the second step we actually parse all the arguments.
    #
    # The detailed strategy is the following:
    # 1. We start with a parser that has all the arguments common to all the movies.
    #    In this, we remove the help flag, as we added our own.
    # 2. We parse the arguments. This is first pass is to understand which movie
    #    the user has selected.
    # 3. We load the movie module, and add the arguments for that movie.
    # 4. We parse again the arguments.

    desc = (
        "Make a video specifying all the details using command-line arguments. "
        "To use this utility, you have to specify a movie. "
        "This code will look for movies in the MOPI_MOVIES_DIR, which you can customize. "
        "To select one of these movies, just pass the file name as first argument. "
        "Alternatively, you can pass the argument -m and specify a file."
    )

    parser = _init_argparse(
        description=desc, add_help=False, formatter_class=RawTextHelpFormatter
    )

    # We have to use this function because the user may have passed arguments
    # that are don't know yet (since we haven't loaded the movie's argument yet)
    parsed, unknown = parser.parse_known_args(cli_args)

    # Now we try to load the movie, if possible. If the user specified a
    # movie-file, that has to have the precedence.

    if parsed.movie_file:
        movie_file = parsed.movie_file
    elif parsed.movie:
        movie_file = os.path.join(parsed.movies_dir, parsed.movie)
    else:
        movie_file = None

    # The case in which the user passed the arguments --only-render-movie and
    # --frame-name-format does not require a movie file. Which means that if the
    # user didn't pass --only-render-movie or --frame-name-format we need the
    # movie file.
    movie_file_required = (
        parsed.only_render_movie is False
    ) or parsed.frame_name_format is None

    if movie_file and movie_file_required:
        # Check if the specified movie file exists.
        if not (os.path.exists(movie_file) and os.path.isfile(movie_file)):
            raise ValueError(f"Movie-file {movie_file} does not exist.")

        # Check if the specified movie file meets the minimum requirements.
        is_movie_file, error_message = _is_movie_file(movie_file)
        if not is_movie_file:
            raise ValueError(error_message)

        # HACK: This is a nuclear way to achieve what we want.
        #
        # We want to import the user-supplied file. We could use importlib for
        # that. However, importing the movie as module introduces significant
        # complications in the parallelization. For instance, the imported file
        # is not in the PYTHONPATH of the various other sub-processes, which
        # makes impossible to pickle `MOPIMovie` (hence, it is impossible to use
        # multiprocessing!).
        #
        # The solution is to simply execute the file in the global scope. If we
        # do that, we can use multiprocessing without any problem.

        exec(open(movie_file).read(), namespace)

        # The user-supplied file can define a function `mopi_add_custom_options`
        # to add additional command-line options.
        if "mopi_add_custom_options" in namespace:
            custom_options = parser.add_argument_group("Movie custom options")
            namespace["mopi_add_custom_options"](custom_options)

    # Update the "help" adding the list of movies detected in the relevant folder.
    available_movies = _search_for_movies(parsed.movies_dir)

    if available_movies:
        epilog = f"Movies found in the MOPI_MOVIES_DIR ({parsed.movies_dir}):"
        for m in available_movies:
            epilog += f"\n* {m}"
    else:
        epilog = f"No movies found in the MOPI_MOVIES_DIR ({parsed.movies_dir})"

    parser.epilog = epilog

    if parsed.help:
        parser.print_help()
        sys.exit(0)

    if not movie_file and movie_file_required:
        raise ValueError("Movie not specified. Please, specify a movie.")

    args = parser.parse_args(cli_args)

    _check_args(args)

    return args
