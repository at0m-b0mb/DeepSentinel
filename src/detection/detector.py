"""Main detector orchestrator — runs all analysis methods and ensembles scores."""

import numpy as np
import cv2
from dataclasses import dataclass, field
from typing import Optional

from .frequency_analysis import fft_artifact_score, ela_score
from .face_analyzer import analyze_face, draw_face_overlay
from .noise_analyzer import noise_consistency_score
from .mesonet import MesoNetDetector


@dataclass
class DetectionResult:
    overall_score: float          # 0 = real, 1 = deepfake
    label: str                    # REAL / SUSPICIOUS / DEEPFAKE
    confidence_pct: float
    fft_score: float
    ela_score: float
    face_score: float
    noise_score: float
    mesonet_score: float          # -1 if unavailable
    faces_found: int
    methods_used: int
    viz_frames: dict = field(default_factory=dict)
    annotated_frame: Optional[np.ndarray] = None


class DeepfakeDetector:
    def __init__(self, weights_path: str | None = None):
        self.mesonet = MesoNetDetector(weights_path)
        # Method enable flags (toggled from settings)
        self.use_fft = True
        self.use_ela = True
        self.use_face = True
        self.use_noise = True
        self.use_mesonet = True

        # Weights for ensemble (calibrated empirically)
        self._weights = {
            "fft":     0.20,
            "ela":     0.20,
            "face":    0.30,
            "noise":   0.20,
            "mesonet": 0.10,
        }

    def analyze(self, image_bgr: np.ndarray, fast: bool = False) -> DetectionResult:
        """Run full detection pipeline on a single frame/image."""
        scores = {}
        viz_frames = {}
        methods_used = 0

        # FFT frequency artifact analysis
        if self.use_fft:
            s, viz = fft_artifact_score(image_bgr)
            scores["fft"] = s
            viz_frames["FFT Spectrum"] = viz
            methods_used += 1
        else:
            scores["fft"] = 0.0

        # Error level analysis (JPEG artifacts)
        if self.use_ela and not fast:
            try:
                s, viz = ela_score(image_bgr)
                scores["ela"] = s
                viz_frames["ELA Map"] = viz
                methods_used += 1
            except Exception:
                scores["ela"] = 0.0
        else:
            scores["ela"] = 0.0

        # Face geometry/boundary analysis
        face_result = None
        if self.use_face:
            face_result = analyze_face(image_bgr)
            scores["face"] = face_result.score
            viz_frames["Face Analysis"] = image_bgr  # will be overlaid
            methods_used += 1
        else:
            scores["face"] = 0.0

        # SRM noise consistency
        if self.use_noise and not fast:
            s, viz = noise_consistency_score(image_bgr)
            scores["noise"] = s
            viz_frames["Noise Residual"] = viz
            methods_used += 1
        else:
            scores["noise"] = 0.0

        # MesoNet neural network
        if self.use_mesonet:
            s = self.mesonet.predict(image_bgr)
            if s >= 0:
                scores["mesonet"] = s
                methods_used += 1
            else:
                scores["mesonet"] = -1.0
        else:
            scores["mesonet"] = -1.0

        overall = self._ensemble(scores, methods_used)

        # Build annotated frame
        annotated = image_bgr.copy()
        if face_result and face_result.faces_found > 0:
            annotated = draw_face_overlay(annotated, face_result, overall)

        label, conf = self._classify(overall)

        return DetectionResult(
            overall_score=overall,
            label=label,
            confidence_pct=conf,
            fft_score=scores["fft"],
            ela_score=scores["ela"],
            face_score=scores["face"],
            noise_score=scores["noise"],
            mesonet_score=scores["mesonet"],
            faces_found=face_result.faces_found if face_result else 0,
            methods_used=methods_used,
            viz_frames=viz_frames,
            annotated_frame=annotated,
        )

    def _ensemble(self, scores: dict, methods_used: int) -> float:
        if methods_used == 0:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for key, w in self._weights.items():
            s = scores.get(key, -1.0)
            if s >= 0:
                weighted_sum += s * w
                total_weight += w

        return float(np.clip(weighted_sum / total_weight, 0.0, 1.0)) if total_weight > 0 else 0.0

    @staticmethod
    def _classify(score: float) -> tuple[str, float]:
        if score >= 0.65:
            return "DEEPFAKE", score * 100
        elif score >= 0.40:
            return "SUSPICIOUS", score * 100
        else:
            return "REAL", (1.0 - score) * 100
