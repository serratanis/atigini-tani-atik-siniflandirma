import unittest
from pathlib import Path

import torch

from src.train_model import CLASS_NAMES, WasteMobileNet, stratified_split


class WasteMobileNetTests(unittest.TestCase):
    def test_model_output_shape(self) -> None:
        model = WasteMobileNet(num_classes=9, pretrained=False)
        model.eval()
        with torch.inference_mode():
            output = model(torch.randn(1, 3, 96, 96))
        self.assertEqual(tuple(output.shape), (1, 9))

    def test_model_produces_finite_values(self) -> None:
        model = WasteMobileNet(num_classes=9, pretrained=False)
        model.eval()
        with torch.inference_mode():
            output = model(torch.zeros(1, 3, 96, 96))
        self.assertTrue(bool(torch.isfinite(output).all()))


class DataSplitTests(unittest.TestCase):
    def test_stratified_split_is_disjoint_and_complete(self) -> None:
        paths = [Path(f"class-{label}/image-{index}.jpg") for label in range(len(CLASS_NAMES)) for index in range(20)]
        labels = [label for label in range(len(CLASS_NAMES)) for _ in range(20)]
        splits = stratified_split(paths, labels, seed=42)
        split_sets = {name: set(values[0]) for name, values in splits.items()}
        self.assertEqual(sum(len(values) for values in split_sets.values()), len(paths))
        self.assertFalse(split_sets["train"] & split_sets["validation"])
        self.assertFalse(split_sets["train"] & split_sets["test"])
        self.assertFalse(split_sets["validation"] & split_sets["test"])
        for _, split_labels in splits.values():
            self.assertEqual(set(split_labels), set(range(len(CLASS_NAMES))))


if __name__ == "__main__":
    unittest.main()
