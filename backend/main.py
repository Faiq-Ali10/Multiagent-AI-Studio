import base64
import os
import time
import asyncio
import tempfile
import uuid
import json
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from Agents.supervisor_agent import ContentSupervisor

MEDIA_DIR = "generated_media"
MAX_FILE_AGE_SECONDS = 100


async def cleanup_old_media():
    """Runs continuously in the background to delete old files."""
    while True:
        try:
            now = time.time()
            if os.path.exists(MEDIA_DIR):
                for filename in os.listdir(MEDIA_DIR):
                    filepath = os.path.join(MEDIA_DIR, filename)
                    if os.path.isfile(filepath):
                        file_age = now.__sub__(os.path.getmtime(filepath))
                        if file_age > MAX_FILE_AGE_SECONDS:
                            os.remove(filepath)
                            print(f"🧹 Janitor deleted old file: {filename}")
        except Exception as e:
            print(f"Janitor error: {e}")

        await asyncio.sleep(120)


@asynccontextmanager
async def lifespan(app: FastAPI):
    janitor_task = asyncio.create_task(cleanup_old_media())
    yield
    janitor_task.cancel()


app = FastAPI(title="AI Creative Studio API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(MEDIA_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

supervisor = ContentSupervisor()
agent = supervisor.get_app()

_video_sessions: dict[str, tuple[str, str]] = {}


class ChatContextMessage(BaseModel):
    role: str
    content: str


class GenerateRequest(BaseModel):
    input: str
    chat_context: list[ChatContextMessage] = []
    planner_summary: str = ""
    previous_music: str = ""
    previous_image: str = ""
    previous_voice: str = ""
    previous_sfx: str = ""
    previous_video: str = ""
    session_id: str = ""
    last_active_agent: str = "None"
    size_choice: int = 3
    target_duration: Optional[int] = None
    previous_settings: Dict[str, Any] = {}


@app.post("/api/upload_video")
async def upload_video(file: UploadFile = File(...)):
    session_id = str(uuid.uuid4())
    suffix = Path(file.filename or "video.mp4").suffix or ".mp4"
    video_bytes = await file.read()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(video_bytes)
    tmp.close()
    _video_sessions[session_id] = (tmp.name, file.filename or "video.mp4")
    return {"session_id": session_id, "filename": file.filename or "video.mp4"}


@app.post("/api/generate", status_code=status.HTTP_200_OK)
async def generate(req: GenerateRequest):
    video_b64 = None
    original_filename = "video.mp4"
    if req.session_id and req.session_id in _video_sessions:
        filepath, original_filename = _video_sessions[req.session_id]
        with open(filepath, "rb") as f:
            video_b64 = base64.b64encode(f.read()).decode("utf8")

    langchain_messages = []
    for past_msg in req.chat_context:
        if past_msg.role == "user":
            langchain_messages.append(HumanMessage(content=past_msg.content))
        else:
            langchain_messages.append(AIMessage(content=past_msg.content))

    langchain_messages.append(HumanMessage(content=req.input))

    initial_state = {
        "messages": langchain_messages,
        "planner_summary": req.planner_summary,
        "step_count": 0,
        "last_music_refined": req.previous_music or None,
        "last_image_refined": req.previous_image or None,
        "last_voice_refined": req.previous_voice or None,
        "last_sfx_refined": req.previous_sfx or None,
        "last_video_refined": req.previous_video or None,
        "video_b64": video_b64,
        "original_filename": original_filename,
        "last_active_agent": req.last_active_agent,
        "size_choice": req.size_choice,
        "sfx_target_duration": req.target_duration,
        "target_duration": req.target_duration,
        "previous_settings": req.previous_settings,
    }

    async def event_generator():
        try:
            final_state = initial_state.copy()
            queue = asyncio.Queue()

            async def run_graph():
                try:
                    async for event in agent.astream(initial_state):
                        await queue.put(("event", event))
                    await queue.put(("done", None))
                except Exception as e:
                    await queue.put(("error", str(e)))

            asyncio.create_task(run_graph())

            while True:
                try:
                    msg_type, data = await asyncio.wait_for(queue.get(), timeout=5.0)

                    if msg_type == "done":
                        break

                    elif msg_type == "error":
                        yield json.dumps({"type": "error", "message": data}) + "\n"
                        return

                    elif msg_type == "event":
                        node_name = list(data.keys())[0]
                        node_data = data[node_name]
                        final_state.update(node_data)

                        if node_name == "supervisor":
                            next_route = node_data.get("next")
                            violation = node_data.get("safety_violation", False)

                            if violation:
                                msg = "🚨 Safety violation occurred! Routing to Dottie"
                            elif next_route == "music_node":
                                msg = "🎵 Generating Music"
                            elif next_route == "image_node":
                                msg = "🖼️ Generating Image"
                            elif next_route == "video_node":
                                msg = "🎥 Generating Video"
                            elif next_route == "sfx_node":
                                msg = "💥 Generating Sound Effects"
                            elif next_route == "voice_over_node":
                                msg = "🗣️ Generating Voiceover"
                            elif next_route == "subtitle_node":
                                msg = "📝 Adding Subtitles"
                            elif next_route == "planner_node":
                                msg = "🧠 Dottie is thinking"
                            else:
                                msg = "✅ Wrapping up"

                            yield json.dumps({"type": "status", "message": msg}) + "\n"

                except asyncio.TimeoutError:
                    yield json.dumps({"type": "ping"}) + "\n"

            media_data = final_state.get("media_data")
            media_type = final_state.get("media_type")
            media_url = None

            if media_data:
                ext = "bin"
                if media_type == "audio":
                    ext = "wav"
                elif media_type == "video":
                    ext = "mp4"
                elif media_type == "image":
                    ext = "jpg"

                filename = f"{uuid.uuid4()}.{ext}"
                filepath = os.path.join("generated_media", filename)

                try:
                    raw_bytes = media_data
                    if isinstance(media_data, str):
                        if media_data.startswith("http"):
                            media_url = media_data
                            raise ValueError("Already a URL")
                        if media_data.startswith("data:"):
                            _, encoded = media_data.split(",", 1)
                            raw_bytes = base64.b64decode(encoded)
                        else:
                            raw_bytes = base64.b64decode(media_data)

                    with open(filepath, "wb") as f:
                        f.write(raw_bytes)

                    media_url = f"http://localhost:8000/media/{filename}"
                    media_data = None
                except Exception as e:
                    print(f"File save skipped: {e}")
                    pass

            messages = final_state.get("messages", [])
            display_text = final_state.get("reasoning", "")

            if messages:
                last_msg = list(reversed(messages))[0]
                if isinstance(last_msg, AIMessage):
                    display_text = last_msg.content

            video_still_valid = final_state.get("video_b64") is not None
            returned_session_id = req.session_id if video_still_valid else ""

            if not video_still_valid and req.session_id in _video_sessions:
                filepath, _ = _video_sessions.pop(req.session_id)
                try:
                    os.unlink(filepath)
                except OSError:
                    pass

            final_payload = {
                "media_url": media_url,
                "media_data": media_data,
                "media_type": media_type,
                "reasoning": display_text,
                "planner_summary": final_state.get("planner_summary", ""),
                "refined_music": final_state.get("last_music_refined") or "",
                "refined_image": final_state.get("last_image_refined") or "",
                "refined_voice": final_state.get("last_voice_refined") or "",
                "refined_sfx": final_state.get("last_sfx_refined") or "",
                "refined_video": final_state.get("last_video_refined") or "",
                "session_id": returned_session_id,
                "last_active_agent": final_state.get("last_active_agent") or "None",
                "size_choice": final_state.get("size_choice", 3),
                "target_duration": final_state.get(
                    "sfx_target_duration", final_state.get("target_duration")
                ),
                "previous_settings": final_state.get("previous_settings") or {},
            }

            final_json_str = json.dumps({"type": "final", "data": final_payload}) + "\n"

            chunk_size = 65536
            for i in range(0, len(final_json_str), chunk_size):
                yield final_json_str[i : i + chunk_size]

        except Exception as e:
            import traceback

            traceback.print_exc()
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"

    return StreamingResponse(event_generator(), media_type="text/plain")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        timeout_keep_alive=300,
        h11_max_incomplete_event_size=5 * 1024 * 1024,
    )
