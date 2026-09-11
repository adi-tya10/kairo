from typing import Annotated
from apps.api.app.core.security import get_current_user
from cv_pipeline.diagram_parser import DiagramComponent, DiagramParser
from fastapi import APIRouter, Depends, HTTPException, status
from packages.schemas.permissions import UserPermissionProfile
from pydantic import BaseModel

router = APIRouter(prefix="/diagrams", tags=["Diagrams"])

class DiagramParseRequest(BaseModel):
    filename: str
    content: str

class DiagramParseResponse(BaseModel):
    filename: str
    component_count: int
    components: list[DiagramComponent]

@router.post("/parse", response_model=DiagramParseResponse, status_code=status.HTTP_200_OK)
async def parse_diagram(
    request_body: DiagramParseRequest,
    current_user: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> DiagramParseResponse:
    """
    Parses architecture diagram / spec document text into structured components.
    Requires authenticated user identity.
    # ponytail: pure JSON payload over python-multipart dependency.
    """
    if not request_body.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename required")

    components = DiagramParser.parse_text_blocks(request_body.content)

    return DiagramParseResponse(
        filename=request_body.filename,
        component_count=len(components),
        components=components,
    )