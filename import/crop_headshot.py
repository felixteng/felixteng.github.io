#!/usr/bin/env python3
"""Detect the face in the source headshot and crop/compress it for the hero photo slot.

CSS slot is 150x188 (display) -> we export at 2x = 300x376 for retina screens.
"""
import cv2
from PIL import Image

SRC = "/Users/tengfei/Projects/academic-site/import/tengf-fei-source.JPG"
OUT = "/Users/tengfei/Projects/academic-site/static/img/teng-fei.jpg"
TARGET_W, TARGET_H = 300, 376  # 2x of the 150x188 CSS box -> ratio 0.7979

img = cv2.imread(SRC)
h, w = img.shape[:2]
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(int(w*0.05), int(w*0.05)))

if len(faces) == 0:
    raise SystemExit("No face detected — falling back to manual crop needed.")

# pick the largest detected face
fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
face_cx, face_cy = fx + fw / 2, fy + fh / 2
print(f"image {w}x{h}; face box {fx},{fy},{fw},{fh}; center {face_cx:.0f},{face_cy:.0f}")

# Build a crop box with the target aspect ratio, sized relative to the face
# so we get a tight head+shoulders portrait (stop above the crossed arms):
# face height ~ 48% of crop height, face in the upper-middle third of the frame.
target_ratio = TARGET_W / TARGET_H  # width / height
crop_h = fh / 0.48
crop_w = crop_h * target_ratio

# clamp to image bounds
crop_h = min(crop_h, h)
crop_w = min(crop_w, w)
crop_h = crop_w / target_ratio if crop_w / crop_h > target_ratio else crop_h
crop_w = crop_h * target_ratio

# vertical: keep ~22% margin above the face top, rest below for shoulders/chest
top = fy - 0.55 * fh
left = face_cx - crop_w / 2

left = max(0, min(left, w - crop_w))
top = max(0, min(top, h - crop_h))

box = (int(left), int(top), int(left + crop_w), int(top + crop_h))
print(f"crop box: {box}")

im = Image.open(SRC)
im = im.crop(box)
im = im.resize((TARGET_W, TARGET_H), Image.LANCZOS)
im = im.convert("RGB")
im.save(OUT, "JPEG", quality=85, optimize=True)
print(f"saved {OUT}  ({im.size[0]}x{im.size[1]})")

import os
print(f"file size: {os.path.getsize(OUT)/1024:.1f} KB")
