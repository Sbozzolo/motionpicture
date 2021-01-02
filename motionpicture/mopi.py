#!/usr/bin/env python3

# Copyright (C) 2020 - 2021 Gabriele Bozzola
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

import logging

from motionpicture.argparse import get_args_movie
from motionpicture import moviemaker as mm

def main():

    args = get_args_movie(globals())

    logger = logging.getLogger(__name__)

    if args.verbose:
        logging.basicConfig(format="%(asctime)s - %(message)s")
        logger.setLevel(logging.INFO)

    logger.info("Initializing MOPIMovie")
    # This is brought into the global namespace by get_args_movie.
    movie = MOPIMovie(args)
    logger.info("MOPIMovie initialized")

    logger.info("Getting frames")
    frames = movie.get_frames()
    logger.info("Frames gotten")

    frame_name_format = mm.prepare_frame_name_format(frames)
    logger.info(f"Chosen frame name format: {frame_name_format}")

    mm.check_outdir(args.outdir, frame_name_format)

    logger.info("Producing frames")
    mm.make_frames(
        movie,
        frames,
        args.outdir,
        frame_name_format,
        parallel=args.parallel,
        num_workers=args.num_workers,
        disable_progress_bar=args.disable_progress_bar,
    )
    logger.info("Frames produced")

    logger.info("Animating frames")
    mm.animate(
        args.movie_name,
        args.extension,
        args.outdir,
        frame_name_format,
        fps=args.fps,
        metadata=mm.metadata_from_args(args)
    )
    logger.info("Video rendered")

    print(f"Movie {args.movie_name} successfully created")

if __name__ == "__main__": # pragma: no cover

    main()
