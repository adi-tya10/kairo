"""
KAIRO Architecture Diagram & Spec Parser.
Extracts component bounding boxes and architecture text to ground decisions.
"""
from dataclasses import dataclass
from pathlib import Path
import re


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
        Parses OCR extracted text lines into diagram components.
        # ponytail: regex-based box heuristic, upgrade to PaddleOCR/Docling model if raw pixel OCR is configured.
        """
        components: list[DiagramComponent] = []
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            # Extract component names like [Billing Service], (Redis Cache), Redis, PostgreSQL
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
    def extract_from_file(file_path: str | Path) -> list[DiagramComponent]:
        p = Path(file_path)
        if not p.exists():
            return []
        content = p.read_text(encoding="utf-8", errors="ignore")
        return DiagramParser.parse_text_blocks(content)
