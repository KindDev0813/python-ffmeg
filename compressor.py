#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jan 10 10:22:16 2021

@author: fox
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan  8 17:29:58 2021

@author: Fabian

Compress video to target size
Resizes and transcodes

This is a CPU intensive process. Need to run on powerful multi-thread instance
for best results.
"""

import os
import ffmpeg


def get_video_info(video_path):

    probe = ffmpeg.probe(video_path)

    size = probe["format"]["size"]
    duration = float(probe["format"]["duration"])
    video_bitrate = probe["format"]["bit_rate"]
    for i in probe["streams"]:
        if "width" in i:
            width = i["width"]
            height = i["height"]
        if "nb_frames" in i:
            fps = float(i["nb_frames"]) / float(duration)
    # if a video has no sound, it won't have audio data values
    audio_stream = next(
        (s for s in probe["streams"] if s["codec_type"] == "audio"), None
    )
    for i in probe["streams"]:
        if audio_stream:
            audio_bitrate = float(audio_stream["bit_rate"])
            audio_channels = audio_stream["channels"]
            audio_codec = audio_stream["codec_name"]
        else:
            audio_bitrate = None
            audio_channels = None
            audio_codec = None
    # audio_bitrate = float(next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)['bit_rate'])
    # audio_channels = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)['channels']
    # audio_codec = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)['codec_name']
    video_codec = next(
        (s for s in probe["streams"] if s["codec_type"] == "video"), None
    )["codec_name"]

    video_info = {
        "probe": probe,
        "video_path": video_path,
        "size": size,
        "width": width,
        "height": height,
        "duration": duration,
        "video_bitrate": video_bitrate,
        "fps": fps,
        "audio_bitrate": audio_bitrate,
        "video_codec": video_codec,
        "audio_codec": audio_codec,
        "audio_channels": audio_channels,
    }
    # improvement needed: need to extract caption file if it exists ffmpeg -i my_file.mkv -f webvtt outfile
    return video_info


def get_precompression_settings(video_info, target_size):

    duration = video_info["duration"]
    audio_bitrate = video_info["audio_bitrate"]
    size_upper_bound = target_size * 1000 * (duration / 60)  # max video size in KB

    total_bitrate_lower_bound = 100 * 1000  # in bps
    min_audio_bitrate = 64 * 1000  # in bps
    max_audio_bitrate = 128 * 1000  # in bps
    min_video_bitrate = 1000 * 1000  # in bps

    """Video quality settings:
    SD: 1,000 kbps video, 128 kbps audio
    HD: 2,000 kbps video, 128 kbps audio (recommended for Vidiren)
    Full HD: 4,500 kbps video, 256 kbps audio"""

    # Target total bitrate, in bps.
    target_total_bitrate = (size_upper_bound * 1024 * 8) / (1.073741824 * duration)
    if target_total_bitrate < total_bitrate_lower_bound:
        print("Bitrate is extremely low! Stop compress!")
        exit()

    # Mininmum size, in kb.
    min_size = (
        (min_audio_bitrate + min_video_bitrate) * (1.073741824 * duration) / (8 * 1024)
    )
    if size_upper_bound < min_size:
        print(
            "Quality not good! Recommended minimum size:",
            "{:,}".format(int(min_size)),
            "KB.",
        )
        exit()

    # target audio bitrate, in bps
    if 10 * audio_bitrate > target_total_bitrate:
        audio_bitrate = target_total_bitrate / 10
    if audio_bitrate < min_audio_bitrate < target_total_bitrate:
        audio_bitrate = min_audio_bitrate
    elif audio_bitrate > max_audio_bitrate:
        audio_bitrate = max_audio_bitrate

    # Target video bitrate, in bps.
    video_bitrate = target_total_bitrate - audio_bitrate
    if video_bitrate < 1000:
        print("Bitrate {} is extremely low! Stop compress.".format(video_bitrate))

    precompression_settings = {
        "target_total_bitrate": target_total_bitrate,
        "min_size": min_size,
        "video_bitrate": video_bitrate,
        "audio_bitrate": audio_bitrate,
    }

    return precompression_settings


def compress_video(video_path, video_bitrate, audio_bitrate):

    filename_suffix = "_compressed"
    filename, extension = os.path.splitext(video_info["video_path"])
    extension = ".mp4"
    compressed_video = filename + filename_suffix + extension
    two_pass = False
    """1 pass is faster than 2 passes. 2-pass does not make a better quality or \
        smaller file: it only lets you set the output file size (but not the quality),\
            whereas -crf lets you choose the quality (but not the file size)."""

    try:
        stream = ffmpeg.input(video_path)
        # stream = ffmpeg.filter(stream, 'fps', fps=30) this filter kills the audio
        if two_pass:
            ffmpeg.output(
                stream,
                "/dev/null" if os.path.exists("/dev/null") else "NUL",
                **{"c:v": "libx264", "b:v": video_bitrate, "pass": 1, "f": "mp4"}
            ).overwrite_output().run()
            ffmpeg.output(
                stream,
                compressed_video,
                **{
                    "c:v": "libx264",
                    "b:v": video_bitrate,
                    "pass": 2,
                    "c:a": "aac",
                    "b:a": audio_bitrate,
                }
            ).overwrite_output().run()
        else:
            ffmpeg.output(
                stream,
                compressed_video,
                **{
                    "c:v": "libx264",
                    "b:v": video_bitrate,
                    "c:a": "aac",
                    "b:a": audio_bitrate,
                }
            ).overwrite_output().run()
    except ffmpeg.Error as e:
        print(e.stderr)
    print("\nAUDIO BITRATE USED FOR COMPRESSION: ", audio_bitrate)
    return compressed_video


def print_data(video_info, precompression_settings, compressed_video):

    print(
        "\nMinimum size threshold: {} kb".format(
            round(precompression_settings["min_size"])
        )
    )
    print(
        "Target total bitrate: {} kbps".format(
            round(precompression_settings["target_total_bitrate"] / 1000)
        )
    )
    print(
        "Target audio bitrate: {} kbps".format(
            round(precompression_settings["audio_bitrate"] / 1000)
        )
    )
    print(
        "Target video bitrate: {} kbps".format(
            round(precompression_settings["video_bitrate"] / 1000)
        )
    )
    print("\nVideo successfully compressed and saved as {}".format(compressed_video))
    print("\nData before compression:")
    print(
        "\nSize: {} MB \nResolution: {}x{} pixels \nDuration: {} sec \n"
        "Video bitrate: {} Kbits per sec \nAudio bitrate {} Kbits per sec \n"
        "Frames per second: {} \nVideo codec: {} \n"
        "Audio codec: {} \nAudio channels: {}".format(
            round(int(video_info["size"]) / 1000000, 1),
            video_info["width"],
            video_info["height"],
            int(video_info["duration"]),
            round(int(video_info["video_bitrate"]) / 1000),
            round(int(video_info["audio_bitrate"]) / 1000),
            int(video_info["fps"]),
            video_info["video_codec"],
            video_info["audio_codec"],
            video_info["audio_channels"],
        )
    )
    print("\nData after compression:")
    compressed_video_info = get_video_info(compressed_video)
    print(
        "\nSize: {} MB \nResolution: {}x{} pixels \nDuration: {} sec \n"
        "Video bitrate: {} Kbits per sec \nAudio bitrate {} Kbits per sec \n"
        "Frames per second: {} \nVideo codec: {} \nAudio codec: {} \nAudio channels: {}".format(
            round(int(compressed_video_info["size"]) / 1000000, 1),
            compressed_video_info["width"],
            compressed_video_info["height"],
            int(compressed_video_info["duration"]),
            round(int(compressed_video_info["video_bitrate"]) / 1000),
            round(int(video_info["audio_bitrate"]) / 1000),
            int(compressed_video_info["fps"]),
            compressed_video_info["video_codec"],
            compressed_video_info["audio_codec"],
            compressed_video_info["audio_channels"],
        )
    )


video_path = "myvideo.mp4"


def main():
    video_info = get_video_info(video_path)
    precompression_settings = get_precompression_settings(
        video_info, target_size=48
    )  # target size in MB per min of video
    compressed_video = compress_video(
        video_path,
        precompression_settings["video_bitrate"],
        precompression_settings["audio_bitrate"],
    )
    print_data(video_info, precompression_settings, compressed_video)
