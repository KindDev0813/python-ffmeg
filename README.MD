Compressor.py is a suite of functions leveraging the ffmpeg framework for compressing and transcoding videos.

srt_generator.py generates the subtitles file(.srt) for a video using google speech api

Install the following before getting started:

    Install python 3.6
    Install ffmpeg (provides free CLI for multimedia editing)
    Install google cloud services


Additionally, I use following terminal commands to rescale videos and images. For fixed width and height -

ffmpeg -i input.avi -vf scale="720:480" output.avi


and if you want to retain aspect ratio just give height as -1 and it will automatically resize based on the width -

ffmpeg -i input.avi -vf scale="720:-1" output.avi

