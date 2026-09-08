# KAIRO: Notion & Multimodal Document Connectors

> **Domain:** Integrations & Connectors  
> **Document ID:** KAIRO-INT-DOCS  
> **Target:** Notion API, Google Drive & Visual Diagram Pipelines

---

## 1. Notion API Sync Connector

1. Create an internal integration at [notion.so/my-integrations](https://www.notion.so/my-integrations).
2. Configure permissions: **Read content**, **Read user information**.
3. Set `NOTION_API_KEY` in `.env`.
4. In Notion, share engineering wikis and technical specifications with the integration.
5. The scheduled sync worker extracts page text, headers, and code blocks, generating chunks with `pgvector` embeddings.

---

## 2. Architecture Diagram Ingestion (CV Pipeline)

When an architecture diagram image (PNG, JPEG) or PDF is uploaded:

```
┌─────────────────┐       ┌────────────────────┐       ┌──────────────────────┐
│ OpenCV Filter   │ ────► │ PaddleOCR / Docling│ ────► │ Spatial Arrow Parser │
│ Contours & Boxes│       │ Text & Layout IoU  │       │ (x1, y1) -> (x2, y2) │
└─────────────────┘       └────────────────────┘       └──────────┬───────────┘
                                                                  │
                                                                  ▼
                                                       ┌──────────────────────┐
                                                       │ Neo4j Subgraph Node  │
                                                       │ [:DEPENDS_ON] Edges  │
                                                       └──────────────────────┘
```

1. **Preprocessing:** Gray-scale conversion, bilateral filtering, and contour dilation isolate service boxes and database cylinders.
2. **Text OCR & Association:** OCR tokens are mapped to structural bounding boxes using Intersection-over-Union (IoU).
3. **Directed Topology Construction:** Arrows $(x_1, y_1) \rightarrow (x_2, y_2)$ create directional `[:COMMUNICATES_WITH]` or `[:DEPENDS_ON]` edges in Neo4j.
4. **Citation Coordinates:** Visual bounding boxes $\{x, y, w, h\}$ are stored in `document_chunks` for UI highlighting.
