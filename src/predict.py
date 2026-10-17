from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
import torch

from train_model import IMAGE_MEAN, IMAGE_STD, load_trained_model, select_device


def prepare_image(path: Path, image_size: int) -> torch.Tensor:
    with Image.open(path) as source:
        image = source.convert("RGB").resize((image_size, image_size), Image.Resampling.BILINEAR)
    array = np.asarray(image, dtype=np.float32) / 255.0
    array = (array - IMAGE_MEAN) / IMAGE_STD
    return torch.from_numpy(array.transpose(2, 0, 1).copy()).unsqueeze(0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Atığını Tanı görüntü tahmini")
    parser.add_argument("image", type=Path)
    parser.add_argument("--model", type=Path, default=Path("models/atigini-tani-mobilenetv2.pt"))
    args = parser.parse_args()

    device = select_device()
    checkpoint = torch.load(args.model, map_location=device, weights_only=True)
    classes = checkpoint["class_names"]
    image_size = int(checkpoint["image_size"])
    model = load_trained_model(checkpoint, device)

    image = prepare_image(args.image, image_size).to(device)
    with torch.inference_mode():
        probabilities = torch.softmax(model(image), dim=1)[0]
    values, indices = probabilities.topk(k=3)

    print(f"Görüntü: {args.image}")
    for rank, (value, index) in enumerate(zip(values.cpu().tolist(), indices.cpu().tolist()), start=1):
        print(f"{rank}. {classes[index]} — %{value * 100:.1f}")
    print("Not: Sonuç karar desteğidir; yerel ayrıştırma kuralları ve insan kontrolü önceliklidir.")


if __name__ == "__main__":
    main()
