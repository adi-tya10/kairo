# KAIRO: Baseline Benchmarks & Evaluation Metrics

> **Domain:** Research, Evaluation & Benchmarks  
> **Document ID:** KAIRO-RES-BENCHMARKS  
> **Target:** Comparative Evaluation & Quantitative Rigor

---

## 1. Experimental Baselines (B1 to B5)

| Baseline | Name | Input & Retrieval Method |
| :--- | :--- | :--- |
| **B1** | **Manual Baseline** | Standard handoff document authored by departing engineer. |
| **B2** | **Vanilla LLM** | Same raw text documents passed to LLM without graph context. |
| **B3** | **Vector RAG** | Indexed chunks in pgvector with Top-$K$ semantic cosine similarity. |
| **B4** | **Standard Graph RAG** | Neo4j graph without temporal validity slicing or CV diagram extraction. |
| **B5** | **KAIRO (Full System)**| Multi-source event ingestion + Temporal Graph + Anomaly Rules + Diagram CV + Cited Synthesis. |

---

## 2. Quantitative Evaluation Metrics

1. **Handoff Completeness Recall ($R_{comp}$):**
   $$R_{comp} = \frac{|\text{Ground Truth Critical Items} \cap \text{Extracted Items}|}{|\text{Ground Truth Critical Items}|}$$
2. **Citation Precision ($P_{cite}$):** Fraction of generated claims whose citations accurately substantiate the statement.
3. **Hidden-Work F1-Score ($F1_{hw}$):** Harmonic mean of precision and recall for detecting seeded inconsistencies.
4. **Context Acquisition Time ($T_{onboard}$):** Time (minutes) for an incoming engineer to master key architectural context.
