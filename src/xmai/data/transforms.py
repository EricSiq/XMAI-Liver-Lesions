"""
Deterministic and reproducible image transforms for B-mode ultrasound.
- Preserves aspect and crops cleanly to 224x224.
- ImageNet normalization.
- Training-only augmentations: horizontal flip, rotation <= 10 deg, brightness/contrast jitter.
- Records original resolution and bounding coordinates for back-projection of explanation heatmaps.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
from PIL import Image
import torch
from torchvision import transforms


def crop_ultrasound_margins(
    img: Image.Image,
    threshold: int = 10,
) -> Tuple[Image.Image, Tuple[int, int, int, int]]:
    """
    Detects and crops uninformative black margins surrounding the active ultrasound fan.
    
    Args:
        img: Input PIL Image.
        threshold: Pixel intensity threshold in [0, 255] below which borders are treated as acoustic void.
        
    Returns:
        Tuple of (cropped_image, (left, top, right, bottom)).
        
    Raises:
        ValueError: If threshold is outside [0, 255] or image dimensions are zero.
    """
    if threshold < 0 or threshold > 255:
        raise ValueError(f"Intensity threshold must be in [0, 255], got {threshold}")
    if img.width == 0 or img.height == 0:
        raise ValueError(f"Cannot process degenerate image with dimensions ({img.width}, {img.height})")

    arr = np.array(img.convert("L"))
    active_rows = np.where(arr.max(axis=1) > threshold)[0]
    active_cols = np.where(arr.max(axis=0) > threshold)[0]

    if len(active_rows) > 0 and len(active_cols) > 0:
        top, bottom = int(active_rows[0]), int(active_rows[-1]) + 1
        left, right = int(active_cols[0]), int(active_cols[-1]) + 1
        # Only crop if at least 5% border was detected to avoid overcropping
        if (right - left) < 0.95 * img.width or (bottom - top) < 0.95 * img.height:
            cropped = img.crop((left, top, right, bottom))
            return cropped, (left, top, right, bottom)

    return img, (0, 0, img.width, img.height)


def get_bmode_transforms(
    is_train: bool = False,
    image_size: int = 224,
) -> transforms.Compose:
    """
    Returns torchvision transforms for B-mode ultrasound images.
    
    Training pipeline incorporates clinically safe geometric and photometric augmentations:
    - Random horizontal flip (p=0.5): liver anatomy is bilaterally variable without changing tumor pathology.
    - Subtle rotation (<=10 deg): simulates probe transducer angle variations.
    - Mild ColorJitter (brightness/contrast <= 0.10): simulates acoustic gain adjustments.
    
    Inference/evaluation pipeline is strictly deterministic:
    - Resize to (image_size, image_size).
    - Conversion to tensor.
    - Standard ImageNet channel normalization.
    """
    if image_size <= 0:
        raise ValueError(f"image_size must be positive, got {image_size}")

    norm = transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    )

    if is_train:
        return transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(degrees=10),
            transforms.ColorJitter(brightness=0.1, contrast=0.1),
            transforms.ToTensor(),
            norm,
        ])
    else:
        return transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            norm,
        ])


def load_bmode_image(
    image_path: Union[str, Path],
    transform: Optional[transforms.Compose] = None,
    auto_crop_margins: bool = False,
) -> Tuple[torch.Tensor, Dict[str, Any]]:
    """
    Loads an ultrasound image file, converts to 3-channel RGB,
    records original resolution and bounding coordinates for explainability,
    and applies torchvision transforms.
    
    Args:
        image_path: String or Path to image file.
        transform: Optional torchvision Compose pipeline.
        auto_crop_margins: Whether to detect and crop black margin borders.
        
    Returns:
        Tuple of (image_tensor, metadata_dict).
        
    Raises:
        FileNotFoundError: If image file does not exist.
        ValueError: If file is not a valid or readable image.
    """
    p = Path(image_path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"Ultrasound image not found at: {p}")

    try:
        with Image.open(p) as img:
            img_rgb = img.convert("RGB")
            orig_w, orig_h = img_rgb.width, img_rgb.height

            if auto_crop_margins:
                img_clean, crop_box = crop_ultrasound_margins(img_rgb)
            else:
                img_clean = img_rgb
                crop_box = (0, 0, orig_w, orig_h)

            tensor = transform(img_clean) if transform else transforms.ToTensor()(img_clean)

            meta = {
                "orig_size": (orig_h, orig_w),
                "crop_box": crop_box,
                "target_size": (tensor.shape[1], tensor.shape[2]),
                "file_path": str(p),
            }

        return tensor, meta
    except Exception as exc:
        if isinstance(exc, FileNotFoundError):
            raise
        raise ValueError(f"Failed to decode ultrasound image '{p}': {exc}") from exc
