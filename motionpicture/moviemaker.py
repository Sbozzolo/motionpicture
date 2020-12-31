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

"""The :py:mod:`~.moviemaker` contains functions to drive the code that renders
the frames and to produce the final video.

One of the key functions is :py:func:`~.animate`, which takes the information on where
the frames are and how to produce the movie, and produces the movie with ffmpeg.

The second import function is :py:func:`~.make_frames`, which takes a ``MOPIMovie``
objects and renders all the required frames.

The additional functions provided are convenience functions to perform string
manipulation or error checking.

"""

import concurrent.futures
import os
from math import ceil, log10

import ffmpeg
from tqdm import tqdm


def check_outdir(output_folder, frame_name_format):
    """Check if the folder where frames should be created exists. If yes, check if
    has already some frames with the same extension has ``frame_name_format``. If yes,
    throw an error.

    (We don't support resuming the creation of frames yet).

    :param output_folder: File where frames have to be saved.
    :type output_folder: str
    :param frame_name_format: C-style format string for frame names.
    :type frame_name_format: str

    """
    if not os.path.isdir(output_folder):
        raise RuntimeError("{output_folder} does not exist")

    # Now we get the extension from frame_name_format
    extension = os.path.splitext(frame_name_format)[-1]

    # Now we find all the files with matching extension
    files_in_outdir_with_ext = {
        f for f in os.listdir(output_folder) if f.endswith(extension)
    }

    has_files = len(files_in_outdir_with_ext) > 0

    if has_files:
        raise RuntimeError(f"Directory {output_folder} already contains images")


def prepare_frame_name_format(frames, extension=".png"):
    """Take the list of frames that have to be generated, and compute the C-style format
    string necessary to accommodate all the frames.

    :param frames: List of frame identifiers.
    :type frames: list
    :param extension: File extension.
    :type extension: str

    :returns: C-style format string for frame names.
    :rtype str
    """
    number_of_digits = ceil(log10(len(frames)))

    extension = sanitize_file_extension(extension)

    return os.path.join(f"%0{number_of_digits}d{extension}")


def sanitize_file_extension(extension):
    """Return file extension that starts with '.' regardless of whether the given one
    had it or not.

    :param extension: File extension.
    :type extension: str

    :returns: File extension starting with '.'
    :rtype: str

    """

    if not extension.startswith("."):
        extension = f".{extension}"

    return extension


def make_frames(
    movie,
    frames,
    output_folder,
    frame_name_format,
    parallel=False,
    num_workers=None,
    disable_progress_bar=False,
):
    """Plot the frames, as directed by the given ``movie``. Optionally, plot frames in
    parallel.

    :param movie: Movie to use for rendering the frames.
    :type movie: ``MOPIMovie``
    :param frames: Which frames to render among the ones specified by
                   ``MOPIMovie.get_frames``.
    :type frames: list
    :param output_folder: Where to save the frames. The folder has to already exist.
                          Already existing frames with the same name will be overwritten.
    :type output_folder: str
    :param frame_name_format: C-style format string for the individual frames.
    :type frame_name_format: str
    :param parallel: If True, render multiple frames at the same time.
    :type parallel: bool
    :param num_workers: Number of frames rendered at the same time. If None, detect the
                        optimal number.
    :type num_workers: int or None
    :param disable_progress_bar: If True, do not display progress bar.
    :type disable_progress_bar: bool
    """
    frame_format_with_dir = os.path.join(output_folder, frame_name_format)

    # tqdm is the pretty progress bar, with estimate of remaining time.
    # It can be disabled passing disable_progress_bar=True
    with tqdm(total=len(frames), unit="frames", disable=disable_progress_bar) as pbar:
        if parallel:
            with concurrent.futures.ProcessPoolExecutor(
                max_workers=num_workers
            ) as executor:
                futures = {
                    executor.submit(
                        movie.make_frame, frame_format_with_dir % frame_num, frame
                    ): frame
                    for frame_num, frame in enumerate(frames)
                }
                for future in concurrent.futures.as_completed(futures):
                    frame_num = futures[future]

                    # We have to retrieve all the results to catch possible exceptions
                    try:
                        future.result()
                    except Exception as exc:
                        print(f"Frame {frame_num} generated an exception: {exc}")
                    pbar.update(1)
        else:
            for frame_num, frame in enumerate(frames):
                path = frame_format_with_dir % frame_num
                try:
                    movie.make_frame(path, frame)
                except Exception as exc:
                    print(f"Frame {frame_num} generated an exception: {exc}")
                pbar.update(1)


def metadata_from_args(args):
    """Extract the metadata fields from the command-line arguments and put them in a
    format ready to be fed to :py:func:`~_process_ffmpeg_metadata`.

    You have to update this when new metadata is added to the args!

    :param args: Command-line arguments.
    :type args: ``argparse.Namespace``

    :returns: Dictionary with metadata and the value.
    :rtype dict

    """
    # You have to update this when new metadata is added to the args!
    return {
        "artist": args.author,
        "comment": args.comment,
        "title": args.title,
    }


def _process_ffmpeg_metadata(metadata):
    """Process a dictionary of metadata in such a way that it can be interpreted by
    ffmpeg.

    :param metadata: Dictionary with keys the metadata fields, and values, the values of
                     the metadata.
    :type metadata: dict

    :returns: Metadata in a ffpmeg-compatible format.
    :rtype: dict

    """
    # Processing metadata following:
    # https://github.com/kkroening/ffmpeg-python/issues/112
    # Here we append the name of the metadata to make unique keys
    return {f"metadata:g:{k}": f"{k}={v}" for k, v in metadata.items()}


def animate(
    movie_name,
    movie_extension,
    output_folder,
    frame_name_format,
    fps=25,
    metadata=None,
    **kwargs,
):
    """Make a movie given the frames.

    Unknown arguments are passed to ffmpeg.

    :param movie_name: Name with extension of where to save the output within
                       ``output_folder``.
    :type movie_name: str
    :param movie_extension: File extension of the video.
    :type movie_extension: str
    :param frame_name_format: Format string for the names of the frames in
                              ``output_folder``.
    :type frame_name_format: str
    :param output_folder: Folder where the frames are saved and the video will be
                          produced.
    :type output_folder: str
    :param fps: Frames-per-second.
    :type fps: int
    :param metadata: Metadata to embed in the output file.
    :type metadata: dict or None

    """

    metadata = _process_ffmpeg_metadata(metadata) if metadata is not None else {}

    movie_file_name = os.path.join(
        output_folder, movie_name + sanitize_file_extension(movie_extension)
    )

    # Assemble movie with ffmpeg
    (
        ffmpeg.input(os.path.join(output_folder, frame_name_format))
        .filter("fps", fps=fps, round="up")
        .output(movie_file_name, **metadata, **kwargs)
        .overwrite_output()
        .run(quiet=True)
    )
