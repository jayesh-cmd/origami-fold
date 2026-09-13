# 🗂️ Paper Fold — Hand Gesture Video Controller

Control a crumpling paper animation in real-time using your hand. Open palm = unfolded. Closed fist = fully crumpled.

---

## Step 1 — Generate Your Paper Fold Photo (ChatGPT)

Use **ChatGPT image generation** (or any compatible AI image tool) with the prompt below to create your subject photo in a folded-paper style.

**Prompt:**

```
-soft distortions where folds bend facial features - slight misalignment between folded sections. composition: - head and body visible - cropped bust - slightly angled (3/4 view) to show depth of folds. details: - clear crease lines across eyes, nose, cheeks, shirt, arms- slight warping of image along folds - subtle paper texture and imperfections. background: - deep black studio background, clean and minimal. lighting: - studio lighting, directional to highlight folds and creases - soft highlights on paper edges, defined shadows. texture: - paper surface with visible fold marks - slight grain. color treatment: - original skin tones preserved but slightly muted. camera: - sharp focus, shallow depth of field. mood: - artistic, sculptural, experimental, editorial. ultra high resolution, no watermark
```

Save the generated image — you'll use it in Step 2.

---

## Step 2 — Generate the Crumpling Video (Kling AI)

Go to **[Kling AI](https://klingai.com)**, upload the image from Step 1, and use the prompt below to animate it.

**Prompt:**

```
Animate this folded paper photo compressing further: existing creases fold inward and tighten, new diagonal creases form, the sculpture crumples into a smaller, denser shape with overlapping angular facets. Keep the same black studio background, same head-on framing, same editorial lighting, same paper texture and skin tones. Static locked camera, no zoom, no hands, no new objects, no text, no watermark.
```

Download the generated `.mp4` video.

---

## Step 3 — Run the Controller

### Prerequisites

```bash
pip install opencv-python mediapipe numpy sounddevice scipy
```

> Also requires **ffmpeg** installed and available in your PATH.

### Setup

1. Place your downloaded video in the same folder as `paper_fold_controller.py`.
2. Open `paper_fold_controller.py` and update `VIDEO_PATH` to your video filename:

```python
VIDEO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "YOUR_VIDEO.MP4")
```

3. Set `CAM_INDEX` to your webcam index (default is `1`, try `0` if it doesn't open).

### Run

```bash
python paper_fold_controller.py
```

### Controls

| Action | Effect |
|---|---|
| Open palm | Video at start (unfolded) |
| Close fist | Video scrubs to end (fully crumpled) |
| `M` | Toggle mirror mode |
| `Q` / `ESC` | Quit |

Two windows open: **Paper Fold** (the animation) and **Hand Tracking** (your webcam feed with landmarks).
