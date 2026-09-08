from cv_pipeline.diagram_parser import DiagramParser


def test_diagram_parser_extracts_components() -> None:
    raw_spec = """
    [Billing Service]
    [Redis Retry Queue]
    [Razorpay Webhook Ingress]
    [PostgreSQL Primary DB]
    """
    components = DiagramParser.parse_text_blocks(raw_spec)
    assert len(components) == 4
    labels = [c.label for c in components]
    assert "Billing Service" in labels
    assert "Redis Retry Queue" in labels
    assert "Razorpay Webhook Ingress" in labels
    assert "PostgreSQL Primary DB" in labels
