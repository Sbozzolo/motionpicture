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

import os
from argparse import Namespace

import pytest

from motionpicture import moviemaker as mm


# This has to be in the global scope to use multiprocessing
class MOPIMovie:
    def get_frames(self):
        return [1, 2, 3]

    def make_frame(self, path, frame):
        # We raise an exception to test that everything still works
        if frame == 2:
            raise RuntimeError

        import matplotlib.pyplot as plt

        plt.plot([1, 2, 3], [4, 5, 6])
        plt.savefig(path)


def test_check_outdir():

    # Folder not existing
    with pytest.raises(RuntimeError):
        mm.check_outdir("bubu", "")

    # Folder already contains images
    with pytest.raises(RuntimeError):
        mm.check_outdir(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_frames"),
            "%d.png",
        )


def test_sanitize_file_extension():

    assert mm.sanitize_file_extension("mp4") == ".mp4"
    assert mm.sanitize_file_extension(".mp4") == ".mp4"


def test_sanitize_snapshot():

    # Snapshot not present
    with pytest.raises(RuntimeError):
        mm.sanitize_snapshot([1, 2], "3")

    # Inhomogenous frames
    with pytest.raises(RuntimeError):
        mm.sanitize_snapshot([1, "2"], 3)

    assert mm.sanitize_snapshot([1.0, 2.0], 1) == 1.0

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

    mm.animate(vid_name, extension, frames_path, "%d.png")

    vid_path = os.path.join(frames_path, vid_name + extension)

    assert os.path.exists(vid_path) is True
    assert os.path.isfile(vid_path) is True

    os.remove(vid_path)


def test_make_frames(tmp_path):

    movie = MOPIMovie()

    d = tmp_path / "frames"
    d.mkdir()

    mm.make_frames(movie, [1, 2, 3], d, "%d.png")

    assert os.path.exists(d / "0.png") is True
    assert os.path.isfile(d / "0.png") is True
    assert os.path.exists(d / "2.png") is True
    assert os.path.isfile(d / "2.png") is True

    # Test in parallel
    d_par = tmp_path / "frames_parallel"
    d_par.mkdir()

    mm.make_frames(
        movie,
        [1, 2, 3],
        d_par,
        "%d.png",
        parallel=True,
        num_workers=1,
        disable_progress_bar=True,
    )

    print(os.listdir(d_par))

    assert os.path.exists(d_par / "0.png") is True
    assert os.path.isfile(d_par / "0.png") is True
    assert os.path.exists(d_par / "2.png") is True
    assert os.path.isfile(d_par / "2.png") is True
