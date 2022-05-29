#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan  8 09:08:35 2021

@author: Fabian

This script:
    - ingests videos
    - transcode them to flac audio
    - upload them to a GC bucket
    - generates an srt file with substitles
    - delete the audio file from GC bucket
"""

import os
import srt
import datetime
import ffmpeg
from google.cloud import speech
from google.cloud import storage

file_name = "beam"

bucket_name = "srt_file_generator"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "rapid-stage-289208-23915bd205ba.json"
gcs_uri = "gs://srt_file_generator/" + file_name + ".flac"
# gcs_uri = "gs://fabian_compression_test/rescue.mp4"
video_path = file_name + ".mp4"
flac_filepath = file_name + ".flac"
storage_object_name = file_name + ".flac"
speech_context = speech.SpeechContext(phrases=["EMK", "EMK products", "Beam Eye Gel"])
"""as an improvement we need to generate a unique set of phrases for each store. Phrases can include:
    - brand name
    - products
    - main SEO keywords"""


def transcode_to_flac(video_path, flac_filepath):
    """Trancodes video files to audio flac files"""
    ffmpeg.input(video_path).output(flac_filepath, ac=1).run()


def upload_to_bucket(bucket_name, flac_filepath, storage_object_name):
    """Uploads a file to the cloud bucket."""

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(storage_object_name)

    blob.upload_from_filename(flac_filepath)

    print("File {} uploaded to bucket: {}.".format(flac_filepath, bucket_name))


def delete_from_bucket(bucket_name, flac_filepath, storage_object_name):

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(storage_object_name)

    blob.delete()


def long_running_recognize(gcs_uri):

    client = speech.SpeechClient()

    """ config = {
        "language_code": "en-US",
        "speech_contexts": speech_context,
        "enable_word_time_offsets": True,
        "model": "video",
        "enable_automatic_punctuation":True
    }"""

    config = speech.RecognitionConfig(
        language_code="en-US",
        speech_contexts=[speech_context],
        enable_word_time_offsets=True,
        model="video",
        enable_automatic_punctuation=True,
    )

    audio = {"uri": gcs_uri}
    operation = client.long_running_recognize(
        request={"config": config, "audio": audio}
    )
    print("Waiting for operation to complete...")
    response = operation.result()
    return response


def subtitle_generation(speech_to_text_response, bin_size=3):
    """We define a bin of time period to display the words in sync with audio.
    Here, bin_size = 3 means each bin is of 3 secs.
    All the words in the interval of 3 secs in result will be grouped togather."""
    transcriptions = []
    index = 0

    for result in response.results:
        try:
            if result.alternatives[0].words[0].start_time.seconds:
                # bin start -> for first word of result
                start_sec = result.alternatives[0].words[0].start_time.seconds
                start_microsec = result.alternatives[0].words[0].start_time.microseconds
            else:
                # bin start -> For First word of response
                start_sec = 0
                start_microsec = 0
            end_sec = start_sec + bin_size  # bin end sec

            # for last word of result
            last_word_end_sec = result.alternatives[0].words[-1].end_time.seconds
            last_word_end_microsec = (
                result.alternatives[0].words[-1].end_time.microseconds
            )

            # bin transcript
            transcript = result.alternatives[0].words[0].word

            index += 1  # subtitle index

            for i in range(len(result.alternatives[0].words) - 1):
                try:
                    word = result.alternatives[0].words[i + 1].word
                    word_start_sec = (
                        result.alternatives[0].words[i + 1].start_time.seconds
                    )
                    word_start_microsec = (
                        result.alternatives[0].words[i + 1].start_time.microseconds
                    )  # 0.001 to convert nana -> micro
                    word_end_sec = result.alternatives[0].words[i + 1].end_time.seconds

                    if word_end_sec < end_sec:
                        transcript = transcript + " " + word
                    else:
                        previous_word_end_sec = (
                            result.alternatives[0].words[i].end_time.seconds
                        )
                        previous_word_end_microsec = (
                            result.alternatives[0].words[i].end_time.microseconds
                        )

                        # append bin transcript
                        transcriptions.append(
                            srt.Subtitle(
                                index,
                                datetime.timedelta(0, start_sec, start_microsec),
                                datetime.timedelta(
                                    0, previous_word_end_sec, previous_word_end_microsec
                                ),
                                transcript,
                            )
                        )

                        # reset bin parameters
                        start_sec = word_start_sec
                        start_microsec = word_start_microsec
                        end_sec = start_sec + bin_size
                        transcript = result.alternatives[0].words[i + 1].word

                        index += 1
                except IndexError:
                    pass
            # append transcript of last transcript in bin
            transcriptions.append(
                srt.Subtitle(
                    index,
                    datetime.timedelta(0, start_sec, start_microsec),
                    datetime.timedelta(0, last_word_end_sec, last_word_end_microsec),
                    transcript,
                )
            )
            index += 1
        except IndexError:
            pass

    # turn transcription list into subtitles
    subtitles = srt.compose(transcriptions)
    return subtitles


if __name__ == "__main__":
    transcode_to_flac(video_path, flac_filepath)
    upload_to_bucket(bucket_name, flac_filepath, storage_object_name)
    response = long_running_recognize(gcs_uri)
    subtitles = subtitle_generation(response)
    with open(file_name + ".srt", "w") as f:
        f.write(subtitles)
    delete_from_bucket(bucket_name, flac_filepath, storage_object_name)
    print("Subtitle file generated")
