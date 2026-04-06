from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

class InferenceEngine:
    """Thread-safe YOLOv8 ONNX inference engine.

    A single InferenceEngine instance can be called concurrently from
    multiple StreamWorker threads — ort.InferenceSession.run() is
    documented thread-safe for concurrent callers.
    """

    def __init__(
        self,
        model_path: str | Path,
        conf: float = 0.25,
        iou: float = 0.45,
    ) -> None:
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        self.session = ort.InferenceSession(str(model_path), providers=providers)
        meta = self.session.get_inputs()[0]
        _, _, h, w = meta.shape          # expected (1, 3, H, W)
        self.input_name = meta.name
        self.output_name = self.session.get_outputs()[0].name
        self.input_h, self.input_w = int(h), int(w)
        self.conf = conf
        self.iou = iou

    def preprocess(self, frame_rgb: np.ndarray) -> np.ndarray:
        img = cv2.resize(frame_rgb, (self.input_w, self.input_h))
        img = img.astype(np.float32) / 255.0
        return img.transpose(2, 0, 1)[np.newaxis]   # (1, 3, H, W)

    def postprocess(self, output: np.ndarray) -> int:
        # YOLOv8 ONNX output shape: (1, 4+num_cls, 8400)
        pred = output[0].T                           # (8400, 4+num_cls)
        scores = pred[:, 4:].max(axis=1)
        mask = scores > self.conf
        pred = pred[mask]
        scores = scores[mask]
        if len(pred) == 0:
            return 0
        cx, cy, bw, bh = pred[:, 0], pred[:, 1], pred[:, 2], pred[:, 3]
        boxes = [
            [float(x), float(y), float(w), float(h)]
            for x, y, w, h in zip(cx - bw / 2, cy - bh / 2, bw, bh)
        ]
        indices = cv2.dnn.NMSBoxes(boxes, scores.tolist(), self.conf, self.iou)
        return len(indices)

    def run(self, frame_rgb: np.ndarray) -> int:
        tensor = self.preprocess(frame_rgb)
        out = self.session.run([self.output_name], {self.input_name: tensor})
        return self.postprocess(out[0])
