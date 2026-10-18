"""
Deterministic and reproducible image transforms for B-mode ultrasound.
- Preserves aspect and crops cleanly to 224x224.
- ImageNet normalization.
- Training-only augmentations: horizontal flip, rotation <= 10 deg, brightness/contrast jitter.
"""

from typing import Tuple
from PIL import Image
import torch
from torchvision import transforms


def get_bmode_transforms(
    is_train: bool = False,
    image_size: int = 224,
) -> transforms.Compose:
    """
    Returns torchvision transforms for B-mode images.
    Inference/evaluation transforms are strictly deterministic.
    """
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


def load_bmode_image(image_path: str, transform: transforms.Compose = None) -> Tuple[torch.Tensor, Tuple[int, int]]:
    """
    Loads an ultrasound image, converts to RGB (3 channels),
    records original resolution (H, W), and applies transform.
    """
    with Image.open(image_path) as img:
        img_rgb = img.convert("RGB")
        orig_size = (img_rgb.height, img_rgb.width)
        tensor = transform(img_rgb) if transform else transforms.ToTensor()(img_rgb)
    return tensor, orig_size
