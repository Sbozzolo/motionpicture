#!/usr/bin/env python3

# Copyright (C) 2020-2023 Gabriele Bozzola
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

import os
import traceback  # Needed by patch_MOPIMovie
from argparse import Namespace

import pytest

from motionpicture import moviemaker as mm
from motionpicture.mopi import patch_MOPIMovie


# This has to be in the global scope to use multiprocessing
class MOPIMovie:
    def __init__(self, args):
        pass

    def get_frames(self):
        return [1, 2, 3]

    def make_frame(self, path, frame):
        # We raise an exception to test that everything still works
        if frame == 2:
            raise RuntimeError

        import matplotlib.pyplot as plt

        plt.plot([1, 2, 3], [4, 5, 6])
        plt.savefig(path)


def test_create_outdir():

    # Folder not existing, we create it
    test_folder = "bubu"
    assert os.path.isdir(test_folder) is False
    mm.create_outdir(test_folder)
    assert os.path.isdir(test_folder) is True
    # Remove the folder
    os.removedirs(test_folder)


def test_check_outdir():

    # Folder already contains images
    test_frame_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "test_frames",
    )

    with pytest.raises(RuntimeError):
        mm.check_outdir(test_frame_folder, "%d.png", "bob", "mp4")

    # ignore_existing_frames = True
    # No error should be thrown
    mm.check_outdir(
        test_frame_folder, "%d.png", "bob", "mp4", ignore_existing_frames=True
    )

    # Let's create a final movie file and check it
    final_file = os.path.join(test_frame_folder, "bob.webm")
    with open(final_file, "w") as _:
        # This creates an empty file
        pass

    with pytest.raises(RuntimeError):
        mm.check_outdir(test_frame_folder, "%d.png", "bob", "webm")

    os.remove(final_file)


def test_get_final_movie_path():

    assert mm.get_final_movie_path("/", "bob", "webm") == "/bob.webm"


def test_sanitize_file_extension():

    assert mm.sanitize_file_extension("mp4") == ".mp4"
    assert mm.sanitize_file_extension(".mp4") == ".mp4"


def test_select_frames():

    frame_list = [1, 2, 10, 15, 20]

    assert mm.select_frames(frame_list) == frame_list
    assert mm.select_frames(frame_list, frame_min=3) == [10, 15, 20]
    assert mm.select_frames(frame_list, frame_max=12) == [1, 2, 10]
    assert mm.select_frames(frame_list, frame_min=3, frame_max=12) == [10]
    assert mm.select_frames(frame_list, frame_min=15, frame_max=15) == [15]
    assert mm.select_frames(frame_list, frame_min=3, frame_every=2) == [10, 20]

    # Wrong type
    assert mm.select_frames(frame_list, frame_min="3", frame_every="2") == [
        10,
        20,
    ]

    with pytest.raises(RuntimeError):
        mm.select_frames([1, "2"], 1, 2)


def test_prepare_frame_name_format():

    assert mm.prepare_frame_name_format([1]) == "%00d.png"
    assert mm.prepare_frame_name_format([1] * 10, ".jpg") == "%01d.jpg"


def test_metadata_from_args():

    expected_out = {
        "artist": "Me",
        "comment": "Bubu",
        "title": "Bob",
    }

    args = Namespace(author="Me", comment="Bubu", title="Bob")

    assert mm.metadata_from_args(args) == expected_out


def test_process_ffmpeg_metadata():

    expected_metadata = {
        "metadata:g:one": "one=1",
        "metadata:g:two": "two=2",
    }

    metadata = {"one": "1", "two": "2"}

    assert mm._process_ffmpeg_metadata(metadata) == expected_metadata


def test_animate():

    frames_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_frames")
    vid_name = "test"
    extension = ".mp4"

    frame_name_folder_with_dir = os.path.join(frames_path, "%d.png")

    mm.animate(vid_name, extension, frame_name_folder_with_dir, overwrite=True)

    vid_path = os.path.join(frames_path, vid_name + extension)

    assert os.path.exists(vid_path) is True
    assert os.path.isfile(vid_path) is True

    os.remove(vid_path)


def test_get_frame_name_format_with_dir():

    assert mm.get_frame_name_format_with_dir("/tmp", "%d.png") == "/tmp/%d.png"


def test_make_frames(tmp_path):

    # We need to patch MOPIMovie
    patch_MOPIMovie(Namespace(verbose=True), globals())

    movie = pMOPIMovie(Namespace())

    d = tmp_path / "frames"
    d.mkdir()

    frame_name_folder_with_dir = os.path.join(d, "%d.png")

    mm.make_frames(movie, {0: 1, 1: 2, 2: 3}, frame_name_folder_with_dir)

    assert os.path.exists(d / "0.png") is True
    assert os.path.isfile(d / "0.png") is True
    assert os.path.exists(d / "2.png") is True
    assert os.path.isfile(d / "2.png") is True

    # Test in parallel
    d_par = tmp_path / "frames_parallel"
    d_par.mkdir()

    frame_name_folder_with_dir = os.path.join(d_par, "%d.png")

    mm.make_frames(
        movie,
        {0: 1, 1: 2, 2: 3},
        frame_name_folder_with_dir,
        parallel=True,
        num_workers=1,
        disable_progress_bar=True,
    )

    print(os.listdir(d_par))

    assert os.path.exists(d_par / "0.png") is True
    assert os.path.isfile(d_par / "0.png") is True
    assert os.path.exists(d_par / "2.png") is True
    assert os.path.isfile(d_par / "2.png") is True
