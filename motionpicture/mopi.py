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
import traceback

from motionpicture import moviemaker as mm
from motionpicture.argparse import get_args_movie


def patch_MOPIMovie(args, namespace):

    # HACK: Patch MOPIMovie to make it more amenable to multiprocessing.
    #
    # The functions in multiprocessing like to take one single argument.
    # However, it is more natural for the user to write a function that
    # takes more. Therefore, we patch MOPIMovie by defining a new class
    # pMOPIMovie with contains a new method p_make_frames which deals with
    # the quirk of multiprocessing. This also includes exception handling.

    # print(globals())

    exec(
        f"""class pMOPIMovie(MOPIMovie):

                def __init__(self, args):
                    super().__init__(args)

                def p_make_frame(self, args):
                    path, frame_num = args
                    try:
                        self.make_frame(path, frame_num)
                    except Exception as exc:
                        print(f"Frame {{frame_num}} generated an exception: {{exc}}")
                        if {args.verbose}:
                            print(traceback.format_exc())
                        else:
                            print("(Run with --verbose for extra debug information)")""",
        namespace,
    )


def main():

    args = get_args_movie(globals())

    logger = logging.getLogger(__name__)

    if args.verbose:
        logging.basicConfig(format="%(asctime)s - %(message)s")
        logger.setLevel(logging.INFO)

    if not args.frame_name_format:

        logger.info("Initializing MOPIMovie")

        # MOPIMovie is brought into the global namespace by get_args_movie,
        # and pMOPIMovie by patch_MOPIMovie

        patch_MOPIMovie(args, globals())

        movie = pMOPIMovie(args)

        logger.info("MOPIMovie initialized")

        logger.info("Getting frames")
        frames = movie.get_frames()
        logger.debug(f"Frames available {frames}")
        logger.info("Frames gotten")

        logger.info("Selecting frames")

        if args.snapshot:
            min_frame = args.snapshot
            max_frame = args.snapshot
            frames_every = 1
        else:
            min_frame = args.min_frame
            max_frame = args.max_frame
            frames_every = args.frames_every

        frames = mm.select_frames(frames, min_frame, max_frame, frames_every)
        logger.debug(f"Frames selected {frames}")
        logger.info("Frames selected")

        frame_name_format = mm.prepare_frame_name_format(frames)
        logger.info(f"Chosen frame name format: {frame_name_format}")

        # frames is a dictionary with keys the frame number and values the frame
        # identifier
        frames_dict = {frame_num: frame for frame_num, frame in enumerate(frames)}

    else:
        logger.debug("Ignoring frame generation")
        frame_name_format = args.frame_name_format
        logger.info(f"Using frame name format: {frame_name_format}")

    mm.create_outdir(args.outdir)

    frame_name_format_with_dir = mm.get_frame_name_format_with_dir(
        args.outdir, frame_name_format
    )

    if args.skip_existing:
        frames_dict = mm.remove_existing_frames(frames_dict, frame_name_format_with_dir)

    # If we overwrite, we don't care if there are already files in outdir
    if not (args.overwrite or args.skip_existing):
        mm.check_outdir(
            args.outdir,
            frame_name_format,
            args.movie_name,
            args.extension,
            args.only_render_movie,
        )

    if not args.only_render_movie:
        logger.info("Producing frames")
        mm.make_frames(
            movie,
            frames_dict,
            frame_name_format_with_dir,
            parallel=args.parallel,
            num_workers=args.num_workers,
            max_tasks_per_child=args.max_tasks_per_child,
            chunk_size=args.chunk_size,
            disable_progress_bar=args.disable_progress_bar,
            verbose=args.verbose,
        )
        logger.info("Frames produced")

    if not args.snapshot:
        logger.info("Animating frames")
        mm.animate(
            args.movie_name,
            args.extension,
            frame_name_format_with_dir,
            codec=args.codec,
            fps=args.fps,
            metadata=mm.metadata_from_args(args),
            verbose=args.verbose,
        )
        logger.info("Video rendered")

        print(f"Movie {args.movie_name} successfully created")


if __name__ == "__main__":  # pragma: no cover

    main()
