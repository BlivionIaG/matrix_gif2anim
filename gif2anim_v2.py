#!/usr/bin/env python3

"""
Copyright 2021 by astro

History: use numpy instead of ImageMagick. 2021/09/25

Note: no support, just read the code and find out how to use it.

1. Install numpy
2. Install Pillow
"""

import sys

from PIL import Image
import numpy as np
import struct

ANIM_HDR = "<4s2HI4H"

ANIM_WIDTH = 80
ANIM_HEIGHT = 80

AUXI_WIDTH = 80
AUXI_HEIGHT = 30

AMFT_WIDTH = 10
AMFT_HEIGHT = 30

SML_WIDTH = 60
SML_HEIGHT = 60

CRS_WIDTH = 128
CRS_HEIGHT = 128


def parse_gif(path):
    im = Image.open(path)
    results = {'size': im.size, 'mode': 'full', 'frames': 0, 'durations': []}
    try:
        while True:
            if im.tile:
                tile = im.tile[0]
                update_region = tile[1]
                update_region_dimensions = update_region[2:]
                if update_region_dimensions != im.size:
                    results['mode'] = 'partial'
                results['frames'] = results['frames'] + 1
                results['durations']. append(im.info['duration'])
            im.seek(im.tell() + 1)
    except EOFError:
        pass
    return results


def convert_to_rgb565(src):
    data = np.asarray(src)
    R = (data[..., 0] >> 3).astype(np.uint16) << 11
    G = (data[..., 1] >> 2).astype(np.uint16) << 5
    B = (data[..., 2] >> 3).astype(np.uint16)
    RGB565 = R | G | B
    return RGB565


def pad_resize(src, dst_size):
    dst = Image.new("RGB", dst_size)
    width, height = src.size
    scale_size = dst_size
    origin_point = (0, 0)
    if width > height:
        scale = scale_size[0]/width
        scale_size = (scale_size[0], int(height*scale))
        origin_point = (0, int((dst_size[1]-scale_size[1])/2))
    else:
        scale = scale_size[1]/height
        scale_size = (int(width*scale), scale_size[1])
        origin_point = (int((dst_size[0]-scale_size[0])/2), 0)

    # print("scaled size: width={}, height={}\n".format(
    #   scale_size[0],
    #   scale_size[1]
    # ))
    scaled_src = src.resize(scale_size, Image.ANTIALIAS)
    # print("pasted origin: x={}, y={}".format(
    #   origin_point[0],
    #   origin_point[1]
    # ))
    dst.paste(scaled_src, origin_point)
    return dst


def process_gif(path, dst_width, dst_height):
    results = parse_gif(path)
    print("size={},mode={},frames={},durations={}\n".format(
            results['size'],
            results['mode'],
            results['frames'],
            results['durations']
    ))
    mode = results['mode']

    im = Image.open(path)

    i = 0
    p = im.getpalette()
    last_frame = im.convert('RGBA')
    files = []

    try:
        while True:
            if not im.getpalette():
                im.putpalette(p)

            new_frame = Image.new('RGBA', im.size)

            if mode == 'partial':
                new_frame.paste(last_frame)

            new_frame.paste(im, (0, 0), im.convert('RGBA'))
            tosave = pad_resize(new_frame, (dst_width, dst_height))
            tosave = convert_to_rgb565(tosave)
            files.append({"data": tosave, "duration": results["durations"][i]})

            i += 1
            last_frame = new_frame
            im.seek(im.tell() + 1)
    except EOFError:
        pass
    return files


def pack_anim(srcs, dst, dst_width, dst_height, anim):
    with open(dst, "wb") as f:
        total = len(srcs)
        hdr_size = struct.calcsize(ANIM_HDR)
        offset = hdr_size + 2*total
        file_size = offset + total*dst_width*dst_height*2
        sig = bytes("AMFT", "utf-8")
        if anim == "anim" or anim == "sml" or anim == "crs":
            sig = bytes("ANIM", "utf-8")

        if anim == "auxi":
            sig = bytes("AUXI", "utf-8")

        d = struct.pack(
            ANIM_HDR,
            sig,
            hdr_size,
            offset,
            file_size,
            dst_width,
            dst_height,
            2,
            total
        )

        # write file header
        f.write(d)
        # write frame durations
        for i in range(total):
            d = struct.pack("<H", srcs[i]["duration"])
            f.write(d)
        # write frame data
        for i in range(total):
            for row in srcs[i]["data"]:
                for pix in row:
                    f.write(struct.pack(">H", pix))


def gif2anim(src, dst, width, height, anim):
    files = process_gif(src, width, height)
    pack_anim(files, dst, width, height, anim)


if __name__ == "__main__":
    if (len(sys.argv) < 3):
        print(
            "Usage: gif2anim in_file out_file \
<anim> | <auxi> | <amft> | <sml> | <crs>"
        )
    else:
        if sys.argv[3] not in ["anim", "auxi", "amft", "sml", "crs"]:
            sys.exit("invalid file format\n")

        width = AMFT_WIDTH
        height = AMFT_HEIGHT

        if sys.argv[3] == "anim":
            width = ANIM_WIDTH
            height = ANIM_HEIGHT

        if sys.argv[3] == "auxi":
            width = AUXI_WIDTH
            height = AUXI_HEIGHT

        if sys.argv[3] == "sml":
            width = SML_WIDTH
            height = SML_HEIGHT

        if sys.argv[3] == "crs":
            width = CRS_WIDTH
            height = CRS_HEIGHT

        gif2anim(sys.argv[1], sys.argv[2], width, height, sys.argv[3])
