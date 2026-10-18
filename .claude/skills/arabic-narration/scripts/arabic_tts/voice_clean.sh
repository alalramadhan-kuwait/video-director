#!/usr/bin/env bash
# تنظيف صوت النماذج المجانية: إزالة الطقطقات والنقرات، تقليل الوشّة، تنعيم السين، ضغط خفيف، وضوح، مستوى موحّد
set -e; IN=$1; OUT=$2
ffmpeg -v error -y -i "$IN" -af "aresample=44100:resampler=soxr,highpass=f=70,adeclick=w=55:o=75:t=2,adeclip,afftdn=nr=12:nf=-42:tn=1,deesser=i=0.35:m=0.5:f=0.5,acompressor=threshold=-21dB:ratio=2.5:attack=6:release=90:makeup=2,equalizer=f=180:t=q:w=1:g=1.5,equalizer=f=3200:t=q:w=1.4:g=2,alimiter=limit=0.89,loudnorm=I=-16:TP=-1.5:LRA=9" -ar 44100 "$OUT"
