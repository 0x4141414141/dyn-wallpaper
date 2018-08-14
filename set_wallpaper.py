"""
    Emulate Mac OS Mojave wallpaper changing transaction based on solar
    position.

    Run with -h flag to see available options.

    This module can be used as standalone, or imported as dependency for other
    uses.
"""
import os
import re
import argparse
import math
from time import sleep
from subprocess import call
from datetime import datetime
from dateutil.tz import tzlocal
from PIL import Image
from astral import Astral


def init_images(folder, set_cmd=False):
    """
        Open all images in the path in the correct order.

        If `set_cmd` is not None, it is used as command for setting the initial
        wallpaper while waiting for the other images to load.
    """
    image_paths = [
        f for f in os.listdir(folder)
        if 'jpeg' in f or 'jpg' in f or 'png' in f
    ]
    # sort images list numerically, not lexicographically, to avoid missing
    # padding 0s problem
    image_paths.sort(key=lambda f: int(re.sub(r'[^0-9]*', "", f)))
    if set_cmd:
        full_path = os.path.join( folder, image_paths[int(len(image_paths)/2)])
        update_wallpaper(set_cmd, full_path)

    image_files = [
        Image.open(os.path.join(folder, f)).convert('RGBA')
        for f in image_paths
    ]
    return (image_paths, image_files)


def init_astral(city):
    """
        Compute the sunrise time and the day length (in seconds) for the
        current timezone. This is done everytime the computer is booted so
        should be enough, unless you are that kind of guy that codes for one
        month without powering off your machine.
    """
    sun = Astral()[city].sun()
    dawn = sun['dawn']
    dusk = sun['dusk']
    day_length = (dusk - dawn).total_seconds()

    return (dawn, dusk, day_length)


def blend_images(img1, img2, amount, tmp_path):
    """
        Take two images path, an amount (0-1, 0 means only img1 is shown, 1
        means only img2 is shown), then store the blended image in /tmp.
    """
    new_img = Image.blend(img1, img2, amount)
    new_img.save(tmp_path, 'PNG', compress_level=1)


def update_wallpaper(cmd, wallpaper_path):
    """
        Use `feh` or a custom command to set the image wallpaper.
    """
    call(cmd.format(wallpaper_path).split())


def get_current_images(dawn_time, day_length, images, dusk_id):
    """
        Get the couple of images needed for the current time, and the
        percentage elapsed between them.

        Basically a mapping from
            [dawn, ..., now, ..., dusk]
        and
            [0,   ...,   len(images)-1]
    """
    now = datetime.now(tzlocal())
    cursor = (now - dawn_time).total_seconds()
    image_id = dusk_id * cursor / day_length
    if image_id < 1 or image_id > len(images) - 1:
        # out of range, just pick last image
        last_image = images[len(images) - 1]
        return (last_image, last_image, 1)
    img1 = images[math.floor(image_id)]
    img2 = images[math.floor(image_id + 1)]
    amount = image_id - math.floor(image_id)
    return (img1, img2, amount)


def main(args):
    """
        Init sun position-based variables, then start loop.
        Check the argument parser for `args` attributes.
    """
    path = os.path.expanduser(args.folder)
    image_paths, images = init_images(path, set_cmd=args.command)

    while True:
        dawn_time, dusk_time, day_length = init_astral(args.city)
        print('Dawn:', str(dawn_time))
        print('Dusk:', str(dusk_time))
        print('Day length (seconds):', str(day_length))

        blend_images(
            *get_current_images(dawn_time, day_length, images, args.dusk_id),
            args.temp
        )
        update_wallpaper(args.command, args.temp)
        sleep(60 * args.rate)


if __name__ == '__main__':
    PARSER = argparse.ArgumentParser(
        description='Live wallpaper based on Sun position, emulating Mac OS \
                     Mojave "dynamic wallpaper".',
        epilog='Source code: https://github.com/Pitasi/live-wallpaper',
    )
    PARSER.add_argument(
        'city',
        help='Timezone city to be used when calculating sunset time (i.e. Rome)\
              see https://astral.readthedocs.io/en/latest/#cities for a list of\
              valid names.'
    )
    PARSER.add_argument(
        'folder',
        help='Folder containing the different wallpapers.',
    )
    PARSER.add_argument(
        '-r',
        '--rate',
        help='Refresh rate in minutes (default 10).',
        type=int,
        default=10,
    )
    PARSER.add_argument(
        '-t',
        '--temp',
        help='Temp image file (default /tmp/wallpaper.png).',
        default='/tmp/wallpaper.png',
    )
    PARSER.add_argument(
        '-i',
        '--dusk-id',
        help='Image number of the "dusk" image (default to 13 for the 16-images\
              Apple set).',
        type=int,
        default=13,
    )
    PARSER.add_argument(
        '-c',
        '--command',
        help='Command to be executed for setting the wallpaper, use "{}" as a \
              placeholder for the image (default: "feh --bg-scale {}").',
        default='feh --bg-scale {}',
    )
    ARGS = PARSER.parse_args()
    main(ARGS)
