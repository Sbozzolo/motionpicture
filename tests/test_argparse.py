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

import argparse
import os

import pytest

from motionpicture import argparse as mopi_argparse


@pytest.fixture(scope="module")
def moviefiles_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_moviefiles")


def test_is_movie_file(moviefiles_path):

    # Here we store some keywords to check if the error messages are correct
    errors = [
        "Python",
        "File",
        "contain a method __init__",
        "it should take 2",
        "get_frames",
        "contain a method make_frame",
        "it should take 3",
        "type",
    ]

    # Invalid
    for num in range(8):
        path = os.path.join(moviefiles_path, f"invalid{num + 1}.py")
        assert mopi_argparse._is_movie_file(path)[0] is False
        assert errors[num] in mopi_argparse._is_movie_file(path)[1]

    # Valid
    path6 = os.path.join(moviefiles_path, f"valid.py")
    assert mopi_argparse._is_movie_file(path6)[0] is True
    assert "" == mopi_argparse._is_movie_file(path6)[1]


def test_search_for_movies(moviefiles_path):

    # Test no file
    folder = os.path.split(mopi_argparse.__file__)[0]
    assert mopi_argparse._search_for_movies(folder) == set()

    # Test one valid file
    assert mopi_argparse._search_for_movies(moviefiles_path) == {"valid.py"}


def test_check_args():

    # Test warning for too many CPUs
    with pytest.warns(Warning):
        args = argparse.Namespace(num_workers=10000)
        mopi_argparse._check_args(args)


def test_get_args_movie(moviefiles_path, capsys):

    # TODO: In these tests we are not testing if the function is
    #       correctly imported!
    #
    # Even if these tests will go thorough the code, we don't know if any
    # problem is arising with the execution of the movie-file.

    # Test help
    with pytest.raises(SystemExit):
        mopi_directory = os.path.split(mopi_argparse.__file__)[0]
        args = ["--movies-dir", mopi_directory, "-h"]
        mopi_argparse.get_args_movie(globals(), cli_args=args)

    # Test epilog with no movies
    captured = capsys.readouterr()
    assert "No movies" in captured.out

    # Test help
    with pytest.raises(SystemExit):
        args = ["--movies-dir", moviefiles_path, "-h"]
        mopi_argparse.get_args_movie(globals(), cli_args=args)

    # Test epilog with movies
    captured = capsys.readouterr()
    assert "Movies" in captured.out

    # Test movie file selected
    args = ["-m", os.path.join(moviefiles_path, "valid.py")]
    new_args = mopi_argparse.get_args_movie(globals(), cli_args=args)
    assert new_args.test is None

    # Test no movie-file selected
    # (This also tests with args = None)
    with pytest.raises(ValueError):
        mopi_argparse.get_args_movie(
            globals(),
        )

    # Test movie-file doesn't exist
    with pytest.raises(ValueError):
        args = ["--movie-file", "lollypop"]
        mopi_argparse.get_args_movie(globals(), cli_args=args)

    # Test also by given movie instead of movie-file
    with pytest.raises(ValueError):
        args = ["lollypop"]
        mopi_argparse.get_args_movie(globals(), cli_args=args)

    # Test invalid movie file
    with pytest.raises(ValueError):
        args = ["-m", os.path.join(moviefiles_path, "invalid1.py")]
        mopi_argparse.get_args_movie(globals(), cli_args=args)

    # Test movie file not needed
    args = ["--only-render-movie", "--frame-name-format", "%03d.png"]
    assert mopi_argparse.get_args_movie(globals(), cli_args=args).movie_file is None
