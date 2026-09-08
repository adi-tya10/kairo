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


@celery_app.task(name="workers.tasks.diagram.evaluate_architecture_drift_task")
def evaluate_architecture_drift_task(
    organization_id: str,
    code_imported_services: list[str],
    diagram_documented_services: list[str],
    repo_id: str = "",
    task_key: str = "",
) -> dict[str, object]:
    """
    Celery task evaluating HW-04 Architecture Documentation Drift asynchronously.
    """
    from apps.api.app.engines.anomaly_rules import AnomalyEngine
    hw04 = AnomalyEngine.evaluate_hw04_architecture_drift(
        code_imported_services=code_imported_services,
        diagram_documented_services=diagram_documented_services,
    )
    return hw04.model_dump()

