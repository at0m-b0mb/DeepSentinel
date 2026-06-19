"""MesoNet deepfake detector — optional neural network method.

Architecture from: "MesoNet: a Compact Facial Video Forgery Detection Network"
Afchar et al., 2018. https://arxiv.org/abs/1809.00888

Requires PyTorch. Gracefully disabled if not available.
Pretrained weights: https://github.com/DariusAf/MesoNet (download separately).
"""

import numpy as np
import cv2

TORCH_AVAILABLE = False
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    pass

INPUT_SIZE = 256  # MesoNet expects 256×256 RGB


class _Meso4(object if not TORCH_AVAILABLE else object):
    pass


if TORCH_AVAILABLE:
    class _Meso4(nn.Module):  # type: ignore[no-redef]
        """Meso4 — 4-block convolutional classifier (156K parameters)."""

        def __init__(self):
            super().__init__()
            self.conv1 = nn.Conv2d(3, 8, 3, padding=1, bias=False)
            self.bn1 = nn.BatchNorm2d(8)
            self.conv2 = nn.Conv2d(8, 8, 5, padding=2, bias=False)
            self.bn2 = nn.BatchNorm2d(8)
            self.conv3 = nn.Conv2d(8, 16, 5, padding=2, bias=False)
            self.bn3 = nn.BatchNorm2d(16)
            self.conv4 = nn.Conv2d(16, 16, 5, padding=2, bias=False)
            self.bn4 = nn.BatchNorm2d(16)
            self.pool = nn.MaxPool2d(2, 2)
            self.dropout = nn.Dropout(0.5)
            self.fc1 = nn.Linear(16 * 16 * 16, 16)
            self.fc2 = nn.Linear(16, 1)

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            x = F.relu(self.bn1(self.conv1(x)))
            x = self.pool(x)
            x = F.relu(self.bn2(self.conv2(x)))
            x = self.pool(x)
            x = F.relu(self.bn3(self.conv3(x)))
            x = self.pool(x)
            x = F.relu(self.bn4(self.conv4(x)))
            x = self.pool(x)
            x = x.reshape(x.size(0), -1)
            x = self.dropout(F.relu(self.fc1(x)))
            return torch.sigmoid(self.fc2(x))


class MesoNetDetector:
    """Wrapper around Meso4 for inference."""

    def __init__(self, weights_path: str | None = None):
        self.available = TORCH_AVAILABLE
        self.loaded = False
        if not TORCH_AVAILABLE:
            return
        self.model = _Meso4()
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        if weights_path:
            self._load_weights(weights_path)

    def _load_weights(self, path: str) -> bool:
        try:
            state = torch.load(path, map_location=self.device, weights_only=True)
            self.model.load_state_dict(state, strict=False)
            self.loaded = True
            return True
        except Exception:
            return False

    def predict(self, image_bgr: np.ndarray) -> float:
        """Return deepfake confidence 0–1. Returns -1 if unavailable."""
        if not self.available or not self.loaded:
            return -1.0
        tensor = _preprocess(image_bgr).to(self.device)
        with torch.no_grad():
            prob = self.model(tensor).item()
        return float(prob)

    @property
    def status(self) -> str:
        if not self.available:
            return "PyTorch not installed"
        if not self.loaded:
            return "Weights not loaded — download from MesoNet repo"
        return "Ready"


def _preprocess(image_bgr: np.ndarray) -> "torch.Tensor":
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (INPUT_SIZE, INPUT_SIZE))
    arr = resized.astype(np.float32) / 255.0
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
    return tensor
