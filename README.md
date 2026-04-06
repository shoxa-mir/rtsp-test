# RTSP Multi-Stream Monitor

A desktop stress-testing harness for CV/image-processing pipelines. Connect up to 40 simultaneous RTSP streams, run YOLOv8 ONNX inference on every Nth frame, and watch CPU, RAM, and GPU load in real time.

## Features

- **Dynamic channels** — add or remove channels at runtime (default 4, min 1, max 40)
- **Per-channel stats** — frames received, FPS (30-frame rolling window), resolution, detection count
- **ONNX GPU inference** — single `InferenceSession` shared across all stream threads (ORT is thread-safe); auto-discovers any `.onnx` model in the project folder
- **System monitor bar** — live CPU %, RAM %, and GPU % progress bars at the bottom
- **Config save/load** — `Ctrl+S` / `Ctrl+O`; nested `.cfg` format with per-channel URL and custom label/tag
- **Exponential backoff reconnect** — 2 s → 4 s → … → 30 s cap on stream errors

## Project Structure

| File | Role |
|------|------|
| `app.py` | Entry point — instantiates `App` |
| `base.py` | `BaseApp` — all UI layout, widgets, system monitor bar |
| `func.py` | `App` — stream lifecycle, inference orchestration, UI refresh loop |
| `capture.py` | `CaptureManager` + `StreamWorker` — PyAV RTSP decode threads |
| `yolo.py` | `InferenceEngine` — YOLOv8 ONNX preprocessing, postprocessing, NMS |

## Setup

```bash
pip install -r requirements.txt
```

## Adding a YOLO model

Export any YOLOv8 model to ONNX and place it next to `app.py`:

```bash
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt').export(format='onnx')"
```

The app auto-discovers the first `*.onnx` file in the project folder on startup. If no model is present, streams still run — inference is simply skipped and detections show `-`.

## Running

```bash
python app.py
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save config |
| `Ctrl+O` | Open config |
| `Ctrl+Q` | Quit |

## Build

`#images should be in icons dir`

```bash
pyinstaller --noconfirm --onefile --windowed --name "RTSP Stress-Test" --add-data "icons/play.png;." --add-data "icons/reconnect.png;." --add-data "icons/stop.png;." app.py
```
