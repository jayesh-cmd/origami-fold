#!/usr/bin/env python3
import cv2
import mediapipe as mp
import numpy as np
import sys
import os
import subprocess
import tempfile
import threading
import sounddevice as sd
import scipy.io.wavfile as wavfile

VIDEO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "BD86A39D-E42F-40D3-BC77-5B16CDBFFD9B.MP4")
CAM_INDEX  = 1

mp_hands   = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils


def compute_openness(hand_landmarks):
    lm    = hand_landmarks.landmark
    wrist = np.array([lm[mp_hands.HandLandmark.WRIST].x,
                      lm[mp_hands.HandLandmark.WRIST].y])
    finger_pairs = [
        (mp_hands.HandLandmark.INDEX_FINGER_TIP,  mp_hands.HandLandmark.INDEX_FINGER_MCP),
        (mp_hands.HandLandmark.MIDDLE_FINGER_TIP, mp_hands.HandLandmark.MIDDLE_FINGER_MCP),
        (mp_hands.HandLandmark.RING_FINGER_TIP,   mp_hands.HandLandmark.RING_FINGER_MCP),
        (mp_hands.HandLandmark.PINKY_TIP,         mp_hands.HandLandmark.PINKY_MCP),
    ]
    projections = []
    for tip_id, mcp_id in finger_pairs:
        tip          = np.array([lm[tip_id].x, lm[tip_id].y])
        mcp          = np.array([lm[mcp_id].x, lm[mcp_id].y])
        wrist_to_mcp = mcp - wrist
        mcp_dist     = np.linalg.norm(wrist_to_mcp)
        if mcp_dist < 1e-6:
            continue
        proj = np.dot(tip - wrist, wrist_to_mcp) / (mcp_dist ** 2)
        projections.append(proj)
    if not projections:
        return 0.5
    raw      = float(np.mean(projections))
    openness = (raw - 0.55) / (1.80 - 0.55)
    return float(np.clip(openness, 0.0, 1.0))


def extract_audio(video_path):
    tmp = tempfile.mktemp(suffix='.wav')
    result = subprocess.run(
        ['ffmpeg', '-y', '-i', video_path, '-vn',
         '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2', tmp],
        capture_output=True
    )
    if result.returncode != 0:
        return None, None, None
    rate, data = wavfile.read(tmp)
    os.unlink(tmp)
    audio = data.astype(np.float32) / 32768.0
    if audio.ndim == 1:
        audio = audio.reshape(-1, 1)
    return rate, audio, audio.shape[1]


def main():
    if not os.path.exists(VIDEO_PATH):
        print(f"Video not found: {VIDEO_PATH}")
        sys.exit(1)

    print("Loading video frames...")
    cap_vid      = cv2.VideoCapture(VIDEO_PATH)
    video_fps    = cap_vid.get(cv2.CAP_PROP_FPS) or 60.0
    video_frames = []
    while True:
        ret, frame = cap_vid.read()
        if not ret:
            break
        video_frames.append(frame)
    cap_vid.release()
    total_frames = len(video_frames)
    print(f"Loaded {total_frames} frames.")

    print("Extracting audio...")
    sample_rate, audio_data, channels = extract_audio(VIDEO_PATH)
    if audio_data is None:
        print("No audio track found.")
        channels = 0

    audio_pos  = [0]
    audio_lock = threading.Lock()
    stream     = None

    if audio_data is not None:
        total_audio_samples = len(audio_data)

        def audio_callback(outdata, frames, time_info, status):
            with audio_lock:
                pos = audio_pos[0]
            n = min(frames, total_audio_samples - pos)
            if n > 0:
                outdata[:n] = audio_data[pos:pos + n]
                with audio_lock:
                    audio_pos[0] = pos + n
            if n < frames:
                outdata[n:] = 0

        stream = sd.OutputStream(
            samplerate=sample_rate,
            channels=channels,
            callback=audio_callback,
            dtype='float32',
            blocksize=512,
        )
        stream.start()
        print("Audio stream started.")

    cap_cam = cv2.VideoCapture(CAM_INDEX)
    if not cap_cam.isOpened():
        print("Could not open webcam.")
        if stream:
            stream.close()
        sys.exit(1)

    mirror         = True
    openness       = 1.0
    last_frame_idx = -1

    cv2.namedWindow("Paper Fold",    cv2.WINDOW_NORMAL)
    cv2.namedWindow("Hand Tracking", cv2.WINDOW_NORMAL)
    cv2.moveWindow("Paper Fold",    0,   50)
    cv2.moveWindow("Hand Tracking", 440, 50)

    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.5,
    ) as hands:
        print("Ready. Open palm = unfolded | Fist = folded | Q/ESC = quit | M = mirror")
        while True:
            ret, cam_frame = cap_cam.read()
            if not ret:
                break

            if mirror:
                cam_frame = cv2.flip(cam_frame, 1)

            rgb              = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            results          = hands.process(rgb)
            rgb.flags.writeable = True

            if results.multi_hand_landmarks:
                hand_lm    = results.multi_hand_landmarks[0]
                black_dot  = mp_drawing.DrawingSpec(color=(0, 0, 0), thickness=2, circle_radius=4)
                black_line = mp_drawing.DrawingSpec(color=(0, 0, 0), thickness=2)
                mp_drawing.draw_landmarks(
                    cam_frame, hand_lm, mp_hands.HAND_CONNECTIONS,
                    black_dot,
                    black_line,
                )
                openness = compute_openness(hand_lm)

            frame_idx = int((1.0 - openness) * (total_frames - 1))
            frame_idx = int(np.clip(frame_idx, 0, total_frames - 1))

            if audio_data is not None and frame_idx != last_frame_idx:
                new_pos = int(frame_idx / total_frames * total_audio_samples)
                with audio_lock:
                    audio_pos[0] = int(np.clip(new_pos, 0, total_audio_samples - 1))
                last_frame_idx = frame_idx

            cv2.imshow("Paper Fold",    video_frames[frame_idx])
            cv2.imshow("Hand Tracking", cam_frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), ord('Q'), 27):
                break
            if key in (ord('m'), ord('M')):
                mirror = not mirror

    if stream:
        stream.stop()
        stream.close()
    cap_cam.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
