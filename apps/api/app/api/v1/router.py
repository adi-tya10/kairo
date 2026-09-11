from fastapi import APIRouter

from apps.api.app.api.v1 import (
    alerts,
    auth,
    chat,
    context,
    diagrams,
    graph,
    handoff,
    health,
    identity,
    sync,
    team,
)
from apps.api.app.api.v1.webhooks import github, gitlab, jira, linear, slack

api_v1_router = APIRouter()
api_v1_router.include_router(auth.router)
api_v1_router.include_router(identity.router)
api_v1_router.include_router(health.router)
api_v1_router.include_router(context.router)
api_v1_router.include_router(handoff.router)
api_v1_router.include_router(chat.router)
api_v1_router.include_router(diagrams.router)
api_v1_router.include_router(sync.router)
api_v1_router.include_router(graph.router)
api_v1_router.include_router(alerts.router)
api_v1_router.include_router(team.router)
api_v1_router.include_router(github.router)
api_v1_router.include_router(jira.router)
api_v1_router.include_router(linear.router)
api_v1_router.include_router(gitlab.router)
api_v1_router.include_router(slack.router)
