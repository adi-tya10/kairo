"""
Celery Task for Async Architecture Diagram & Spec Document Ingestion.
"""
from cv_pipeline.diagram_parser import DiagramParser
from workers.celery_app import celery_app


@celery_app.task(name="tasks.process_diagram_document")
def process_diagram_document(raw_text: str, document_id: str) -> dict[str, object]:
    """
    Parses architectural components from uploaded document text in background.
    # ponytail: reuse DiagramParser.parse_text_blocks directly.
    """
    components = DiagramParser.parse_text_blocks(raw_text)
    return {
        "document_id": document_id,
        "component_count": len(components),
        "components": [{"label": c.label, "confidence": c.confidence} for c in components],
    }
