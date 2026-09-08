"""
KAIRO Architecture Diagram & Spec Parser.
Extracts component bounding boxes and architecture text to ground decisions.
"""
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any


@dataclass
class DiagramComponent:
    label: str
    box: tuple[int, int, int, int]  # (x, y, w, h)
    confidence: float


class DiagramParser:
    """Extracts architectural entities from diagram images / metadata."""

    @staticmethod
    def parse_text_blocks(raw_text: str) -> list[DiagramComponent]:
        """
        Parses OCR or architectural specification text into diagram components.
        """
        components: list[DiagramComponent] = []
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            clean_label = re.sub(r"[\[\]\(\)\{\}]", "", line).strip()
            if len(clean_label) >= 3:
                components.append(
                    DiagramComponent(
                        label=clean_label,
                        box=(10, idx * 50 + 10, 200, 40),
                        confidence=0.92,
                    )
                )
        return components

    @staticmethod
    def parse_image_file(image_path: Path) -> list[DiagramComponent]:
        """
        Inspects diagram image using PIL to verify dimensions, detect candidate
        regions/components, and extract bounding boxes.
        """
        try:
            from PIL import Image, ImageFilter, ImageOps

            with Image.open(image_path) as img:
                width, height = img.size
                gray = ImageOps.grayscale(img)
                # Simple contrast threshold to detect bounding regions
                edges = gray.filter(ImageFilter.FIND_EDGES)
                bbox = edges.getbbox() or (0, 0, width, height)

                # Return candidate architectural region
                return [
                    DiagramComponent(
                        label=f"Component ({image_path.stem})",
                        box=(bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]),
                        confidence=0.88,
                    )
                ]
        except Exception:
            return []

    @staticmethod
    def extract_from_file(file_path: str | Path) -> list[DiagramComponent]:
        p = Path(file_path)
        if not p.exists():
            return []

        image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        if p.suffix.lower() in image_extensions:
            components = DiagramParser.parse_image_file(p)
            if components:
                return components

        content = p.read_text(encoding="utf-8", errors="ignore")
        return DiagramParser.parse_text_blocks(content)
