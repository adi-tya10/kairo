"""
KAIRO Parameterized LLM Prompt Templates.
Enforces strict citation grounding and prompt-injection safety boundaries.
"""

from packages.prompts.qa_v1 import (
    GROUNDED_QA_SYSTEM_PROMPT,
    GROUNDED_QA_USER_TEMPLATE,
)
from packages.prompts.synthesis_v1 import (
    HANDOFF_SYNTHESIS_SYSTEM_PROMPT,
    HANDOFF_SYNTHESIS_USER_TEMPLATE,
)

__all__ = [
    "GROUNDED_QA_SYSTEM_PROMPT",
    "GROUNDED_QA_USER_TEMPLATE",
    "HANDOFF_SYNTHESIS_SYSTEM_PROMPT",
    "HANDOFF_SYNTHESIS_USER_TEMPLATE",
]
