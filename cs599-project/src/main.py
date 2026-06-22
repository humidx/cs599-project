from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import FileResponse

from src.config import settings
from src.models import ChatRequest, ChatResponse
from src.planner import PlannerAgent

app = FastAPI(title=settings.app_name, version="0.1.0")
agent = PlannerAgent()
WEB_DIR = Path(__file__).parent / "web"


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "planner": "llm" if settings.llm_api_key else "local"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or str(uuid4())
    reply, status, profile, sources = await agent.respond(session_id, request.message)
    return ChatResponse(session_id=session_id, reply=reply, status=status, profile=profile, sources=sources)

