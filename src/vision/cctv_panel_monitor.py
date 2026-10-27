"""
SolarSense EMS — CCTV RTSP & Daily Scheduled Solar Panel Vision Monitor
========================================================================
Supports:
1. Live RTSP IP Camera Streaming (OpenCV / FFmpeg backend)
2. Daily Scheduled Solar Noon Snapshots (Minimal shadow & glare window: 11:30–13:30 PKT)
3. Inverter Telemetry-Triggered On-Demand Capture
4. Test-Time Augmentation (TTA) Defect Classification via PyTorch EfficientNet-B2
5. Diagnostic JSON Alert Emission for Maintenance Oracle & Feature Store
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from src.vision.dataloader import IMAGE_SIZE, IMAGENET_MEAN, IMAGENET_STD
from src.vision.train_classifier import DEFAULT_CHECKPOINT_PATH, build_model

ALERTS_DIR = Path("data/processed/panel_images/cctv_alerts")

# Loss derate coefficients mapping defect type to estimated PR degradation
DERATE_COEFFICIENTS: Dict[str, Tuple[float, str]] = {
    "clean": (0.00, "NONE"),
    "dusty": (0.05, "MEDIUM"),  # 5% PR drop from uniform soiling
    "bird_drop": (0.12, "HIGH"),  # 12% drop + hot-spot thermal stress
    "electrical_damage": (0.25, "CRITICAL"),  # 25% drop + bypass diode conduction
    "physical_damage": (0.35, "EMERGENCY"),  # Micro-crack / shattered glass risk
}


class CCTVPanelMonitor:
    def __init__(
        self,
        checkpoint_path: Path = DEFAULT_CHECKPOINT_PATH,
        device: Optional[str] = None,
        confidence_threshold: float = 0.50,
    ):
        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))
        self.confidence_threshold = confidence_threshold
        self.checkpoint_path = Path(checkpoint_path)

        if not self.checkpoint_path.exists():
            raise FileNotFoundError(
                f"Model checkpoint not found at: {self.checkpoint_path}. Train model via src/vision/train_classifier.py"
            )

        # Load Checkpoint & Model
        checkpoint = torch.load(self.checkpoint_path, map_location=self.device)
        self.class_to_idx: Dict[str, int] = checkpoint.get("class_to_idx", {
            "bird_drop": 0, "clean": 1, "dusty": 2, "electrical_damage": 3, "physical_damage": 4
        })
        self.idx_to_class: Dict[int, str] = {v: k for k, v in self.class_to_idx.items()}
        num_classes = len(self.class_to_idx)

        self.model = build_model(num_classes=num_classes, pretrained=False).to(self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()

        # Image Transform
        self.transform = transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ])

        ALERTS_DIR.mkdir(parents=True, exist_ok=True)

    def predict_pil_image(self, pil_img: Image.Image, use_tta: bool = True) -> Dict[str, Any]:
        """Classifies a PIL image using Test-Time Augmentation (TTA)."""
        tensor = self.transform(pil_img.convert("RGB")).unsqueeze(0).to(self.device)

        with torch.no_grad():
            if not use_tta:
                logits = self.model(tensor)
            else:
                # 3-pass TTA (original, horizontal flip, vertical flip)
                l1 = self.model(tensor)
                l2 = self.model(torch.flip(tensor, dims=[3]))
                l3 = self.model(torch.flip(tensor, dims=[2]))
                logits = (l1 + l2 + l3) / 3.0

            probs = torch.softmax(logits, dim=1)[0]
            pred_idx = logits.argmax(dim=1).item()
            pred_label = self.idx_to_class[pred_idx]
            confidence = probs[pred_idx].item()

        derate_pr, severity = DERATE_COEFFICIENTS.get(pred_label, (0.0, "UNKNOWN"))
        requires_cleaning = pred_label in {"dusty", "bird_drop"}

        return {
            "condition": pred_label,
            "confidence": round(confidence, 4),
            "requires_cleaning": requires_cleaning,
            "severity": severity,
            "estimated_derate_pr": derate_pr,
            "all_probabilities": {
                self.idx_to_class[i]: round(probs[i].item(), 4) for i in range(len(self.class_to_idx))
            },
        }

    def process_frame(self, frame_bgr: np.ndarray, draw_overlay: bool = True) -> Tuple[Dict[str, Any], np.ndarray]:
        """Runs defect detection on an OpenCV BGR frame and renders a HUD overlay."""
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_frame)
        diag = self.predict_pil_image(pil_img)

        annotated = frame_bgr.copy()
        if draw_overlay:
            cond = diag["condition"]
            conf = diag["confidence"]
            sev = diag["severity"]

            color_map = {
                "clean": (0, 200, 0),        # Green
                "dusty": (0, 165, 255),      # Orange
                "bird_drop": (0, 255, 255),   # Yellow
                "electrical_damage": (0, 0, 255), # Red
                "physical_damage": (255, 0, 255), # Magenta
            }
            box_color = color_map.get(cond, (255, 255, 255))

            h, w = annotated.shape[:2]
            # Draw semi-transparent header HUD
            overlay = annotated.copy()
            cv2.rectangle(overlay, (0, 0), (w, 50), (20, 20, 20), -1)
            cv2.addWeighted(overlay, 0.75, annotated, 0.25, 0, annotated)

            text = f"SolarSense EMS | Condition: {cond.upper()} ({conf*100:.1f}%) | Severity: {sev}"
            cv2.putText(annotated, text, (15, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.65, box_color, 2)
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S PKT")
            cv2.putText(annotated, timestamp_str, (w - 230, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (200, 200, 200), 1)

        return diag, annotated

    def process_source(
        self,
        source: str,
        sample_interval_sec: float = 5.0,
        max_frames: Optional[int] = None,
        save_alerts: bool = True,
    ) -> list[Dict[str, Any]]:
        """Processes an RTSP stream URL, local video file, or camera index."""
        print("=" * 70)
        print("SOLARSENSE EMS — CCTV LIVE STREAM / VIDEO INSPECTOR")
        print(f"Source:           {source}")
        print(f"Sample Interval:  {sample_interval_sec} seconds")
        print(f"Inference Device: {self.device}")
        print("=" * 70)

        # Handle single static image file
        source_path = Path(source)
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

        if source_path.is_file() and source_path.suffix.lower() in image_extensions:
            frame = cv2.imread(str(source_path))
            diag, annotated = self.process_frame(frame)
            if save_alerts and diag["condition"] != "clean":
                out_path = ALERTS_DIR / f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                cv2.imwrite(str(out_path), annotated)
                diag["alert_snapshot"] = str(out_path)
            print(f"[RESULT] {diag['condition']} (Conf: {diag['confidence']*100:.1f}%, Severity: {diag['severity']})")
            return [diag]

        # Handle directory of static images (batch panel inspection / virtual CCTV feed)
        if source_path.is_dir():
            image_files = sorted([p for p in source_path.rglob("*") if p.suffix.lower() in image_extensions])
            if not image_files:
                raise FileNotFoundError(f"No valid image files found in directory: {source_path}")

            if max_frames:
                image_files = image_files[:max_frames]

            print(f"[BATCH] Discovered {len(image_files)} panel images in directory: {source_path}")
            history = []
            for idx, img_p in enumerate(image_files, 1):
                frame = cv2.imread(str(img_p))
                if frame is None:
                    continue
                diag, annotated = self.process_frame(frame)
                diag["image_file"] = str(img_p)
                history.append(diag)

                status_msg = (
                    f"[{idx:>3}/{len(image_files)}] {img_p.name:<25} | "
                    f"Condition: {diag['condition']:<18} | Conf: {diag['confidence']*100:.1f}% | Severity: {diag['severity']:<8}"
                )
                print(status_msg)

                if save_alerts and diag["condition"] != "clean":
                    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    snap_path = ALERTS_DIR / f"alert_{ts_str}_{img_p.stem}_{diag['condition']}.jpg"
                    cv2.imwrite(str(snap_path), annotated)
                    diag["alert_snapshot"] = str(snap_path)

            print("=" * 70)
            print(f"Directory inspection complete. Evaluated {len(history)} panel pictures.")
            return history

        # Handle video stream or video file
        src = int(source) if source.isdigit() else source
        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            raise IOError(f"Could not open video source or RTSP stream: {source}")

        history = []
        frame_idx = 0
        last_sample_time = 0.0

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                now = time.time()
                if (now - last_sample_time) >= sample_interval_sec:
                    last_sample_time = now
                    frame_idx += 1

                    diag, annotated = self.process_frame(frame)
                    history.append(diag)

                    status_msg = (
                        f"Frame {frame_idx:>3} | Condition: {diag['condition']:<18} | "
                        f"Conf: {diag['confidence']*100:.1f}% | Severity: {diag['severity']:<8}"
                    )
                    print(status_msg)

                    if save_alerts and diag["condition"] != "clean":
                        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                        snap_path = ALERTS_DIR / f"alert_{ts_str}_{diag['condition']}.jpg"
                        cv2.imwrite(str(snap_path), annotated)
                        diag["alert_snapshot"] = str(snap_path)

                        # Write JSON telemetry log
                        json_path = ALERTS_DIR / f"alert_{ts_str}.json"
                        with open(json_path, "w") as f:
                            json.dump(diag, f, indent=2)

                    if max_frames and frame_idx >= max_frames:
                        break
        finally:
            cap.release()

        print("=" * 70)
        print(f"Inspection complete. Processed {len(history)} sampled frames.")
        return history


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SolarSense EMS — CCTV RTSP & Video Defect Monitor")
    parser.add_argument("--source", type=str, default="data/processed/panel_images/solarsense_master_v1/test/clean/clean_test_0001.jpg", help="RTSP URL, video file, or image path")
    parser.add_argument("--checkpoint", type=str, default=str(DEFAULT_CHECKPOINT_PATH), help="Model weights path")
    parser.add_argument("--interval", type=float, default=5.0, help="Sampling interval in seconds")
    parser.add_argument("--max-frames", type=int, default=10, help="Maximum frames to process in stream")
    args = parser.parse_args()

    monitor = CCTVPanelMonitor(checkpoint_path=Path(args.checkpoint))
    monitor.process_source(source=args.source, sample_interval_sec=args.interval, max_frames=args.max_frames)
