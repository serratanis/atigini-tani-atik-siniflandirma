from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import random
import time
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageEnhance, ImageOps
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForImageClassification, MobileNetV2Config, MobileNetV2ForImageClassification


CLASS_NAMES = [
    "Cardboard",
    "Food Organics",
    "Glass",
    "Metal",
    "Miscellaneous Trash",
    "Paper",
    "Plastic",
    "Textile Trash",
    "Vegetation",
]
MODEL_NAME = "google/mobilenet_v2_1.0_224"
IMAGE_MEAN = np.array([0.5, 0.5, 0.5], dtype=np.float32)
IMAGE_STD = np.array([0.5, 0.5, 0.5], dtype=np.float32)

PROJECT = Path(__file__).resolve().parent.parent
FIGURES = PROJECT / "figures"
RESULTS = PROJECT / "results"
MODELS = PROJECT / "models"
DATA_DIR = PROJECT / "data"


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.backends.mps.is_available():
        torch.mps.manual_seed(seed)


def select_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def collect_samples(data_dir: Path) -> tuple[list[Path], list[int]]:
    paths: list[Path] = []
    labels: list[int] = []
    for label, class_name in enumerate(CLASS_NAMES):
        class_dir = data_dir / class_name
        if not class_dir.is_dir():
            raise FileNotFoundError(f"Sınıf klasörü bulunamadı: {class_dir}")
        class_paths = sorted(
            path for path in class_dir.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
        )
        paths.extend(class_paths)
        labels.extend([label] * len(class_paths))
    if not paths:
        raise RuntimeError("Veri setinde görüntü bulunamadı.")
    return paths, labels


def audit_exact_duplicates(paths: list[Path], labels: list[int]) -> dict[str, object]:
    """Aynı dosya içeriğinin farklı bölmelere sızmasını eğitimden önce engeller."""
    seen: dict[str, tuple[Path, int]] = {}
    duplicates: list[dict[str, object]] = []
    for path, label in zip(paths, labels):
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        if digest in seen:
            first_path, first_label = seen[digest]
            duplicates.append(
                {
                    "sha256": digest,
                    "first_path": str(first_path),
                    "duplicate_path": str(path),
                    "same_label": first_label == label,
                }
            )
        else:
            seen[digest] = (path, label)
    if duplicates:
        raise RuntimeError(
            f"{len(duplicates)} tam içerik kopyası bulundu. Veri sızıntısını önlemek için "
            "kopyalar temizlenmeden eğitim durduruldu."
        )
    return {"algorithm": "SHA-256", "exact_duplicate_groups": 0, "files_checked": len(paths)}


def stratified_split(
    paths: list[Path], labels: list[int], seed: int
) -> dict[str, tuple[list[Path], list[int]]]:
    train_paths, temp_paths, train_labels, temp_labels = train_test_split(
        paths,
        labels,
        test_size=0.30,
        random_state=seed,
        stratify=labels,
    )
    val_paths, test_paths, val_labels, test_labels = train_test_split(
        temp_paths,
        temp_labels,
        test_size=0.50,
        random_state=seed,
        stratify=temp_labels,
    )
    return {
        "train": (train_paths, train_labels),
        "validation": (val_paths, val_labels),
        "test": (test_paths, test_labels),
    }


def save_split_manifest(splits: dict[str, tuple[list[Path], list[int]]], data_root: Path) -> None:
    lines = ["split,relative_path,class_name,class_index"]
    for split_name, (paths, labels) in splits.items():
        for path, label in sorted(zip(paths, labels), key=lambda pair: str(pair[0])):
            lines.append(
                f'{split_name},"{path.relative_to(data_root).as_posix()}","{CLASS_NAMES[label]}",{label}'
            )
    (DATA_DIR / "splits.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")


class WasteDataset(Dataset):
    def __init__(self, paths: list[Path], labels: list[int], image_size: int, augment: bool) -> None:
        self.paths = paths
        self.labels = labels
        self.image_size = image_size
        self.augment = augment

    def __len__(self) -> int:
        return len(self.paths)

    def _augment(self, image: Image.Image) -> Image.Image:
        if random.random() < 0.5:
            image = ImageOps.mirror(image)
        if random.random() < 0.7:
            image = image.rotate(random.uniform(-12, 12), resample=Image.Resampling.BILINEAR)
        if random.random() < 0.5:
            image = ImageEnhance.Brightness(image).enhance(random.uniform(0.88, 1.12))
        if random.random() < 0.5:
            image = ImageEnhance.Contrast(image).enhance(random.uniform(0.88, 1.12))
        return image

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int, str]:
        path = self.paths[index]
        with Image.open(path) as source:
            image = source.convert("RGB")
        if self.augment:
            image = self._augment(image)
        image = image.resize((self.image_size, self.image_size), Image.Resampling.BILINEAR)
        array = np.asarray(image, dtype=np.float32) / 255.0
        array = (array - IMAGE_MEAN) / IMAGE_STD
        tensor = torch.from_numpy(array.transpose(2, 0, 1).copy())
        return tensor, self.labels[index], str(path)


class WasteMobileNet(nn.Module):
    """ImageNet ön-eğitimli MobileNetV2'yi dokuz RealWaste sınıfına uyarlar."""

    def __init__(
        self,
        num_classes: int,
        *,
        pretrained: bool = True,
        config: dict[str, object] | None = None,
    ) -> None:
        super().__init__()
        id2label = {index: name for index, name in enumerate(CLASS_NAMES[:num_classes])}
        label2id = {name: index for index, name in id2label.items()}
        if config is not None:
            self.backbone = MobileNetV2ForImageClassification(MobileNetV2Config.from_dict(config))
        elif pretrained:
            mobile_config = MobileNetV2Config.from_pretrained(MODEL_NAME)
            mobile_config.num_labels = num_classes
            mobile_config.id2label = id2label
            mobile_config.label2id = label2id
            self.backbone = AutoModelForImageClassification.from_pretrained(
                MODEL_NAME,
                config=mobile_config,
                ignore_mismatched_sizes=True,
            )
        else:
            mobile_config = MobileNetV2Config(
                num_labels=num_classes,
                id2label=id2label,
                label2id=label2id,
            )
            self.backbone = MobileNetV2ForImageClassification(mobile_config)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.backbone(pixel_values=inputs).logits


def load_trained_model(checkpoint: dict[str, object], device: torch.device) -> WasteMobileNet:
    model = WasteMobileNet(
        len(checkpoint["class_names"]),
        pretrained=False,
        config=checkpoint["model_config"],
    ).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model


def class_weights(labels: list[int], device: torch.device) -> torch.Tensor:
    counts = Counter(labels)
    total = len(labels)
    weights = [total / (len(CLASS_NAMES) * counts[index]) for index in range(len(CLASS_NAMES))]
    return torch.tensor(weights, dtype=torch.float32, device=device)


def run_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    optimizer: torch.optim.Optimizer | None = None,
) -> tuple[float, float]:
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    total_correct = 0
    total_count = 0
    context = torch.enable_grad() if training else torch.inference_mode()
    with context:
        for images, targets, _ in loader:
            images = images.to(device)
            targets = targets.to(device)
            if training:
                optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = criterion(logits, targets)
            if training:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()
            batch_size = targets.size(0)
            total_loss += loss.item() * batch_size
            total_correct += (logits.argmax(dim=1) == targets).sum().item()
            total_count += batch_size
    return total_loss / total_count, total_correct / total_count


def predict(model: nn.Module, loader: DataLoader, device: torch.device):
    model.eval()
    all_targets: list[int] = []
    all_predictions: list[int] = []
    all_confidences: list[float] = []
    all_top2: list[list[int]] = []
    all_paths: list[str] = []
    with torch.inference_mode():
        for images, targets, paths in loader:
            logits = model(images.to(device))
            probabilities = torch.softmax(logits, dim=1)
            confidence, prediction = probabilities.max(dim=1)
            top2 = probabilities.topk(k=2, dim=1).indices
            all_targets.extend(targets.tolist())
            all_predictions.extend(prediction.cpu().tolist())
            all_confidences.extend(confidence.cpu().tolist())
            all_top2.extend(top2.cpu().tolist())
            all_paths.extend(paths)
    return all_targets, all_predictions, all_confidences, all_top2, all_paths


def create_eda(paths: list[Path], labels: list[int], seed: int) -> None:
    plt.rcParams.update({"font.family": "Arial", "axes.titleweight": "bold"})
    counts = Counter(labels)
    values = [counts[index] for index in range(len(CLASS_NAMES))]
    fig, ax = plt.subplots(figsize=(11, 5.8))
    bars = ax.bar(CLASS_NAMES, values, color="#2D6A63")
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_title("RealWaste sınıf dağılımı")
    ax.set_ylabel("Görüntü sayısı")
    ax.tick_params(axis="x", rotation=28)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / "01-sinif-dagilimi.png", dpi=180)
    plt.close(fig)

    rng = random.Random(seed)
    fig, axes = plt.subplots(3, 3, figsize=(9, 9))
    for label, ax in enumerate(axes.flat):
        candidates = [path for path, target in zip(paths, labels) if target == label]
        sample = rng.choice(candidates)
        with Image.open(sample) as image:
            ax.imshow(image.convert("RGB"))
        ax.set_title(CLASS_NAMES[label], fontsize=10)
        ax.axis("off")
    fig.suptitle("Her sınıftan gerçek ortam örneği", fontsize=16, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGURES / "02-sinif-ornekleri.png", dpi=180)
    plt.close(fig)

    brightness: list[list[float]] = [[] for _ in CLASS_NAMES]
    for path, label in zip(paths, labels):
        with Image.open(path) as image:
            gray = image.convert("L").resize((32, 32), Image.Resampling.BILINEAR)
            brightness[label].append(float(np.asarray(gray, dtype=np.float32).mean()))
    fig, ax = plt.subplots(figsize=(11, 5.8))
    ax.boxplot(brightness, tick_labels=CLASS_NAMES, patch_artist=True, boxprops={"facecolor": "#A7C4A0"})
    ax.set_title("Sınıflara göre görüntü parlaklığı dağılımı")
    ax.set_ylabel("Ortalama gri seviye (0–255)")
    ax.tick_params(axis="x", rotation=28)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / "03-parlaklik-dagilimi.png", dpi=180)
    plt.close(fig)


def plot_history(history: list[dict[str, float]]) -> None:
    epochs = [row["epoch"] for row in history]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].plot(epochs, [row["train_loss"] for row in history], label="Eğitim", color="#173F3A")
    axes[0].plot(epochs, [row["val_loss"] for row in history], label="Validation", color="#E76F51")
    axes[0].set_title("Loss eğrileri")
    axes[0].set_xlabel("Epoch")
    axes[0].legend()
    axes[1].plot(epochs, [row["train_accuracy"] for row in history], label="Eğitim", color="#173F3A")
    axes[1].plot(epochs, [row["val_accuracy"] for row in history], label="Validation", color="#E76F51")
    axes[1].set_title("Accuracy eğrileri")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylim(0, 1)
    axes[1].legend()
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(FIGURES / "04-egitim-egrileri.png", dpi=180)
    plt.close(fig)


def plot_confusion(matrix: np.ndarray) -> None:
    normalized = matrix / matrix.sum(axis=1, keepdims=True)
    fig, ax = plt.subplots(figsize=(9.6, 8.2))
    image = ax.imshow(normalized, cmap="Greens", vmin=0, vmax=1)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label="Satır içi oran")
    ax.set_xticks(range(len(CLASS_NAMES)), CLASS_NAMES, rotation=45, ha="right")
    ax.set_yticks(range(len(CLASS_NAMES)), CLASS_NAMES)
    ax.set_xlabel("Tahmin")
    ax.set_ylabel("Gerçek sınıf")
    ax.set_title("Normalize confusion matrix")
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            value = normalized[row, column]
            ax.text(column, row, f"{value:.2f}\n({matrix[row, column]})", ha="center", va="center", fontsize=7, color="white" if value > 0.55 else "#20332E")
    fig.tight_layout()
    fig.savefig(FIGURES / "05-confusion-matrix.png", dpi=180)
    plt.close(fig)


def plot_error_gallery(
    targets, predictions, confidences, paths, data_root: Path
) -> list[dict[str, object]]:
    errors = [
        {"path": path, "true": true, "pred": pred, "confidence": confidence}
        for true, pred, confidence, path in zip(targets, predictions, confidences, paths)
        if true != pred
    ]
    errors.sort(key=lambda row: float(row["confidence"]), reverse=True)
    chosen = errors[:12]
    fig, axes = plt.subplots(3, 4, figsize=(12, 9))
    for ax, row in zip(axes.flat, chosen):
        with Image.open(str(row["path"])) as image:
            ax.imshow(image.convert("RGB"))
        ax.set_title(
            f"Gerçek: {CLASS_NAMES[int(row['true'])]}\nTahmin: {CLASS_NAMES[int(row['pred'])]} ({float(row['confidence']):.0%})",
            fontsize=8,
        )
        ax.axis("off")
    for ax in axes.flat[len(chosen):]:
        ax.axis("off")
    fig.suptitle("En güvenli yanlış tahminler", fontsize=16, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGURES / "06-hata-galerisi.png", dpi=180)
    plt.close(fig)
    return [
        {
            **row,
            "path": Path(str(row["path"])).relative_to(data_root).as_posix(),
        }
        for row in chosen
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--patience", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--evaluate-only",
        action="store_true",
        help="Mevcut en iyi checkpoint'i eğitmeden test eder ve tüm sonuç dosyalarını üretir.",
    )
    args = parser.parse_args()

    for directory in [FIGURES, RESULTS, MODELS, DATA_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    set_seed(args.seed)
    device = select_device()

    paths, labels = collect_samples(args.data_dir)
    duplicate_audit = audit_exact_duplicates(paths, labels)
    create_eda(paths, labels, args.seed)
    splits = stratified_split(paths, labels, args.seed)
    save_split_manifest(splits, args.data_dir)

    train_paths, train_labels = splits["train"]
    val_paths, val_labels = splits["validation"]
    test_paths, test_labels = splits["test"]
    train_dataset = WasteDataset(train_paths, train_labels, args.image_size, augment=True)
    val_dataset = WasteDataset(val_paths, val_labels, args.image_size, augment=False)
    test_dataset = WasteDataset(test_paths, test_labels, args.image_size, augment=False)
    generator = torch.Generator().manual_seed(args.seed)
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=0, generator=generator)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)

    model_path = MODELS / "atigini-tani-mobilenetv2.pt"
    history_path = RESULTS / "training_history.json"
    start_time = time.perf_counter()
    if args.evaluate_only:
        if not model_path.exists() or not history_path.exists():
            raise FileNotFoundError("Değerlendirme için checkpoint ve training_history.json gereklidir.")
        history = json.loads(history_path.read_text(encoding="utf-8"))
        best_val_loss = min(row["val_loss"] for row in history)
        checkpoint = torch.load(model_path, map_location=device, weights_only=True)
        model = load_trained_model(checkpoint, device)
    else:
        model = WasteMobileNet(len(CLASS_NAMES), pretrained=True).to(device)
        weights = class_weights(train_labels, device)
        criterion = nn.CrossEntropyLoss(weight=weights)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=2)
        history: list[dict[str, float]] = []
        best_val_loss = math.inf
        patience_left = args.patience
        for epoch in range(1, args.epochs + 1):
            train_loss, train_accuracy = run_epoch(model, train_loader, criterion, device, optimizer)
            val_loss, val_accuracy = run_epoch(model, val_loader, criterion, device)
            scheduler.step(val_loss)
            row = {
                "epoch": epoch,
                "train_loss": train_loss,
                "train_accuracy": train_accuracy,
                "val_loss": val_loss,
                "val_accuracy": val_accuracy,
                "learning_rate": optimizer.param_groups[0]["lr"],
            }
            history.append(row)
            history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(row, ensure_ascii=False), flush=True)
            if val_loss < best_val_loss - 1e-4:
                best_val_loss = val_loss
                patience_left = args.patience
                torch.save(
                    {
                        "model_state": model.state_dict(),
                        "model_config": model.backbone.config.to_dict(),
                        "class_names": CLASS_NAMES,
                        "image_size": args.image_size,
                        "seed": args.seed,
                        "architecture": "MobileNetV2 transfer learning",
                        "source_model": MODEL_NAME,
                    },
                    model_path,
                )
            else:
                patience_left -= 1
                if patience_left == 0:
                    break
        checkpoint = torch.load(model_path, map_location=device, weights_only=True)
        model = load_trained_model(checkpoint, device)
    targets, predictions, confidences, top2, prediction_paths = predict(model, test_loader, device)
    accuracy = accuracy_score(targets, predictions)
    precision, recall, f1, _ = precision_recall_fscore_support(
        targets, predictions, average="macro", zero_division=0
    )
    weighted_precision, weighted_recall, weighted_f1, _ = precision_recall_fscore_support(
        targets, predictions, average="weighted", zero_division=0
    )
    top2_accuracy = float(np.mean([target in guesses for target, guesses in zip(targets, top2)]))
    matrix = confusion_matrix(targets, predictions, labels=list(range(len(CLASS_NAMES))))
    report = classification_report(
        targets,
        predictions,
        labels=list(range(len(CLASS_NAMES))),
        target_names=CLASS_NAMES,
        output_dict=True,
        zero_division=0,
    )
    errors = plot_error_gallery(targets, predictions, confidences, prediction_paths, args.data_dir)
    plot_history(history)
    plot_confusion(matrix)

    with (RESULTS / "test_predictions.csv").open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target)
        writer.writerow(["relative_path", "true_class", "predicted_class", "confidence", "top2", "correct"])
        for path, true, predicted, confidence, guesses in zip(
            prediction_paths, targets, predictions, confidences, top2
        ):
            writer.writerow(
                [
                    Path(path).relative_to(args.data_dir).as_posix(),
                    CLASS_NAMES[true],
                    CLASS_NAMES[predicted],
                    f"{confidence:.8f}",
                    " | ".join(CLASS_NAMES[index] for index in guesses),
                    true == predicted,
                ]
            )

    class_counts = Counter(labels)
    majority_baseline = max(class_counts.values()) / len(labels)
    elapsed = time.perf_counter() - start_time
    metrics = {
        "dataset": {
            "name": "RealWaste",
            "instances": len(paths),
            "classes": CLASS_NAMES,
            "class_counts": {CLASS_NAMES[key]: value for key, value in sorted(class_counts.items())},
            "license": "CC BY-NC-SA 4.0 (conservative; UCI record states CC BY 4.0)",
            "doi": "10.24432/C5SS4G",
        },
        "split": {name: len(values[0]) for name, values in splits.items()},
        "model": {
            "name": "Atığını Tanı MobileNetV2 Transfer Learning",
            "source_model": MODEL_NAME,
            "pretraining": "ImageNet-1k",
            "parameters": sum(parameter.numel() for parameter in model.parameters()),
            "image_size": args.image_size,
            "epochs_completed": len(history),
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "best_validation_loss": best_val_loss,
            "pipeline_seconds": elapsed,
            "run_mode": "evaluate_only" if args.evaluate_only else "train_and_evaluate",
            "device": str(device),
        },
        "test": {
            "accuracy": accuracy,
            "macro_precision": precision,
            "macro_recall": recall,
            "macro_f1": f1,
            "weighted_precision": weighted_precision,
            "weighted_recall": weighted_recall,
            "weighted_f1": weighted_f1,
            "top2_accuracy": top2_accuracy,
            "majority_baseline_accuracy": majority_baseline,
        },
        "classification_report": report,
        "confusion_matrix": matrix.tolist(),
        "history": history,
        "high_confidence_errors": errors,
        "reproducibility": {
            "seed": args.seed,
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "exact_duplicate_audit": duplicate_audit,
        },
    }
    (RESULTS / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metrics["test"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
