#!/bin/bash
# export.sh PRESET IN OUT [extra -vf filters]
# Presets: reel (1080x1920 IG/TikTok), square (1080x1080), feed (1080x1350), yt (1920x1080), 4k (3840x2160), master (ProRes 422 HQ)
# All: -14 LUFS / -1 dBTP loudness, high-quality x264, faststart.
set -e; P=$1; IN=$2; OUT=$3; X=${4:+,$4}
case $P in reel) S=1080:1920;; square) S=1080:1080;; feed) S=1080:1350;; yt) S=1920:1080;; 4k) S=3840:2160;; master) S=;; *) echo "bad preset"; exit 1;; esac
VF="${S:+scale=$S:force_original_aspect_ratio=decrease:flags=lanczos,pad=$S:(ow-iw)/2:(oh-ih)/2:black,}setsar=1$X"
A=(-af "loudnorm=I=-14:TP=-1:LRA=11" -ar 48000)
if [ "$P" = master ]; then ffmpeg -v error -y -i "$IN" -vf "$VF" -c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le "${A[@]}" -c:a pcm_s24le "$OUT"
else ffmpeg -v error -y -i "$IN" -vf "$VF" -c:v libx264 -preset slow -crf 17 -profile:v high -pix_fmt yuv420p -r 30 -g 60 -bf 2 \
  -movflags +faststart "${A[@]}" -c:a aac -b:a 320k "$OUT"; fi
ffprobe -v error -show_entries stream=codec_name,width,height:format=duration -of compact "$OUT"
