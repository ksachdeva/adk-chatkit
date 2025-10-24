import mimetypes
from typing import Any

from adk_chatkit import ADKContext
from chatkit.server import StreamingResult
from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from starlette.responses import JSONResponse

from backend._config import Settings
from backend.agents.knowledge import DOCUMENTS, DOCUMENTS_BY_ID, KnowledgeAssistantChatkitServer, as_dicts

router = APIRouter(route_class=DishkaRoute)


@router.post("/chatkit")
async def chatkit_endpoint(
    request: Request,
    settings: FromDishka[Settings],
    request_server: FromDishka[KnowledgeAssistantChatkitServer],
) -> Response:
    payload = await request.body()
    print("Received payload:", payload)

    user_id = "ksachdeva-1"

    result = await request_server.process(
        payload,
        ADKContext(user_id=user_id, app_name=settings.KNOWLEDGE_APP_NAME),
    )

    print(result)

    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    if hasattr(result, "json"):
        return Response(content=result.json, media_type="application/json")
    return JSONResponse(result)


@router.get("/health", summary="Check health of facts agent")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/documents")
async def list_documents() -> dict[str, Any]:
    return {"documents": as_dicts(DOCUMENTS)}


@router.get("/documents/{document_id}/file")
async def document_file(
    document_id: str,
    settings: FromDishka[Settings],
) -> FileResponse:
    document = DOCUMENTS_BY_ID.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = settings.DATA_DIR / "knowledge" / document.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not available")

    media_type, _ = mimetypes.guess_type(str(file_path))
    headers = {"Content-Disposition": f'inline; filename="{document.filename}"'}
    return FileResponse(
        file_path,
        media_type=media_type or "application/octet-stream",
        headers=headers,
    )


@router.get("/threads/{thread_id}/citations")
async def thread_citations(
    thread_id: str,
    settings: FromDishka[Settings],
    request_server: FromDishka[KnowledgeAssistantChatkitServer],
) -> dict[str, Any]:
    user_id = "ksachdeva-1"
    context = ADKContext(user_id=user_id, app_name=settings.KNOWLEDGE_APP_NAME)

    try:
        citations = await request_server.latest_citations(thread_id, context=context)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    document_ids = sorted({citation["document_id"] for citation in citations})

    return {"documentIds": [document_ids], "citations": citations}
