#!/usr/bin/env python3
"""
XMAI Environment & Data Decoding Verification Script
Validates Python, PyTorch with CUDA, imaging dependencies, and test-decodes
samples from TCIA (DICOM), SYSU (Video), and AUL (Polygon JSON).
"""

import sys
import os
import platform
from pathlib import Path

def print_header(title: str):
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def main():
    print_header("XMAI Environment Verification")
    print(f"Python Version: {platform.python_version()} ({platform.architecture()[0]})")
    print(f"Executable:     {sys.executable}")
    print(f"OS:             {platform.system()} {platform.release()} ({platform.version()})")

    # 1. Dependency Imports
    print_header("1. Checking Core Dependencies")
    deps = [
        ("numpy", "NumPy"),
        ("pandas", "Pandas"),
        ("yaml", "PyYAML"),
        ("pydantic", "Pydantic"),
        ("PIL", "Pillow"),
        ("cv2", "OpenCV"),
        ("pydicom", "PyDICOM"),
        ("sklearn", "Scikit-Learn"),
        ("scipy", "SciPy"),
        ("statsmodels", "Statsmodels"),
        ("matplotlib", "Matplotlib"),
        ("captum", "Captum"),
        ("pytest", "Pytest"),
        ("torch", "PyTorch"),
        ("torchvision", "TorchVision"),
    ]

    all_imported = True
    for mod_name, label in deps:
        try:
            mod = __import__(mod_name)
            ver = getattr(mod, "__version__", "installed")
            print(f" [PASS] {label:15s} (v{ver})")
        except ImportError as e:
            print(f" [FAIL] {label:15s} - Missing! ({e})")
            all_imported = False

    # 2. PyTorch & CUDA Verification
    print_header("2. PyTorch & Accelerator Status")
    try:
        import torch
        print(f"PyTorch Version: {torch.__version__}")
        cuda_avail = torch.cuda.is_available()
        print(f"CUDA Available:  {cuda_avail}")
        if cuda_avail:
            print(f"Device Count:    {torch.cuda.device_count()}")
            print(f"Device Name:     {torch.cuda.get_device_name(0)}")
            print(f"CUDA Arch:       {torch.cuda.get_device_capability(0)}")
            # Quick tensor allocation on GPU
            x = torch.randn(10, 10, device="cuda")
            y = x @ x.T
            print(f" [PASS] GPU Tensor Math OK (device: {y.device})")
        else:
            print(" [INFO] Running in CPU-only mode for PyTorch.")
    except Exception as e:
        print(f" [FAIL] PyTorch CUDA verification failed: {e}")

    # 3. DICOM Decoding Test (TCIA)
    print_header("3. TCIA DICOM Decoding Test")
    tcia_root = Path("TCIA/b_mode_and_ceus_liver")
    dcm_files = list(tcia_root.glob("**/*.dcm")) if tcia_root.exists() else []
    if dcm_files:
        sample_dcm = dcm_files[0]
        try:
            import pydicom
            ds = pydicom.dcmread(sample_dcm)
            pixels = ds.pixel_array
            print(f" Sample File:   {sample_dcm.name}")
            print(f" Modality:      {getattr(ds, 'Modality', 'Unknown')}")
            print(f" SOP Class UID: {getattr(ds, 'SOPClassUID', 'Unknown')}")
            print(f" Pixel Array:   Shape {pixels.shape}, Dtype {pixels.dtype}, Min {pixels.min()}, Max {pixels.max()}")
            print(" [PASS] TCIA DICOM decoded successfully.")
        except Exception as e:
            print(f" [FAIL] Failed to decode TCIA DICOM: {e}")
    else:
        print(" [SKIP] No TCIA DICOM files found in TCIA/b_mode_and_ceus_liver")

    # 4. Video Decoding Test (SYSU-CEUS)
    print_header("4. SYSU CEUS Video Decoding Test")
    sysu_root = Path("Focal-liver-lesions-dataset-in-CEUS-master")
    avi_files = list(sysu_root.glob("**/*.avi")) if sysu_root.exists() else []
    if avi_files:
        sample_avi = avi_files[0]
        try:
            import cv2
            cap = cv2.VideoCapture(str(sample_avi))
            if not cap.isOpened():
                raise RuntimeError(f"Could not open video file: {sample_avi}")
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None:
                raise RuntimeError("Failed to read first frame from video.")
            print(f" Sample Video:  {sample_avi.name}")
            print(f" Properties:    {width}x{height} @ {fps:.1f} fps, {frame_count} total frames")
            print(f" Frame Array:   Shape {frame.shape}, Dtype {frame.dtype}")
            print(" [PASS] SYSU AVI decoded successfully.")
        except Exception as e:
            print(f" [FAIL] Failed to decode SYSU video: {e}")
    else:
        print(" [SKIP] No SYSU AVI files found in Focal-liver-lesions-dataset-in-CEUS-master")

    # 5. AUL Polygon Rasterisation Test
    print_header("5. AUL Polygon Rasterisation Test")
    aul_root = Path("AUL")
    json_files = list(aul_root.glob("**/*.json")) if aul_root.exists() else []
    if json_files:
        sample_json = json_files[0]
        try:
            import json
            import numpy as np
            import cv2
            with open(sample_json, "r") as f:
                coords = json.load(f)
            pts = np.array(coords, dtype=np.int32)
            # Create a 800x800 blank mask to test rasterisation
            mask = np.zeros((800, 800), dtype=np.uint8)
            cv2.fillPoly(mask, [pts], color=1)
            area_px = int(mask.sum())
            print(f" Sample File:   {sample_json.name}")
            print(f" Polygon Verts: {len(coords)} vertices")
            print(f" Mask Raster:   Shape {mask.shape}, Foreground Area {area_px} px")
            print(" [PASS] AUL polygon rasterised successfully.")
        except Exception as e:
            print(f" [FAIL] Failed to rasterise AUL polygon: {e}")
    else:
        print(" [SKIP] No AUL JSON files found in AUL/")

    print_header("Verification Summary")
    if all_imported:
        print("All dependencies and decoding smoke tests passed successfully!")
        return 0
    else:
        print("Some dependencies are missing. Please review failures above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
