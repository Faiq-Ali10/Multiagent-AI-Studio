import streamlit as st
import requests
import base64
import os
import json
from dotenv import load_dotenv

# === Configuration ===
load_dotenv()
API_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/generate")
_base_url = API_URL.rsplit("/api/", 1)[0]
UPLOAD_URL = os.getenv("UPLOAD_URL", f"{_base_url}/api/upload_video")

st.set_page_config(page_title="AI Creative Studio", page_icon="🎨", layout="centered")

# === Session State (Expanded for ALL Configurations) ===
if "music_context" not in st.session_state:
    st.session_state.music_context = ""
if "image_context" not in st.session_state:
    st.session_state.image_context = ""
if "voice_context" not in st.session_state:
    st.session_state.voice_context = ""
if "sfx_context" not in st.session_state:
    st.session_state.sfx_context = ""
if "video_context" not in st.session_state:
    st.session_state.video_context = ""

# === NEW MEMORY VARIABLES ===
if "last_active_agent" not in st.session_state:
    st.session_state.last_active_agent = "None"
if "size_choice" not in st.session_state:
    st.session_state.size_choice = 3
if "target_duration" not in st.session_state:
    st.session_state.target_duration = None
if "previous_settings" not in st.session_state:
    st.session_state.previous_settings = {}
if "planner_summary" not in st.session_state:
    st.session_state.planner_summary = ""
# ============================

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "video_session_id" not in st.session_state:
    st.session_state.video_session_id = ""
if "video_filename" not in st.session_state:
    st.session_state.video_filename = "video.mp4"

# === Minimal Sidebar ===
st.sidebar.title("🎨 AI Creative Studio")

with st.sidebar.expander("🧠 Agent Memory Bank", expanded=True):
    st.write(f"**🤖 Last Agent:** `{st.session_state.last_active_agent}`")
    st.write(f"**🗣️ Voice:** {st.session_state.voice_context or 'None'}")
    st.write(f"**💥 SFX:** {st.session_state.sfx_context or 'None'}")
    st.write(f"**🎵 Music:** {st.session_state.music_context or 'None'}")
    st.write(f"**🖼️ Image:** {st.session_state.image_context or 'None'}")
    st.write(f"**🎥 Gen Video:** {st.session_state.video_context or 'None'}")
    st.write(
        f"**📎 Uploaded:** {st.session_state.video_filename if st.session_state.video_session_id else 'None'}"
    )

if st.sidebar.button("🗑️ Clear All Memory"):
    st.session_state.chat_history = []
    st.session_state.music_context = ""
    st.session_state.image_context = ""
    st.session_state.voice_context = ""
    st.session_state.sfx_context = ""
    st.session_state.video_context = ""

    # Reset new variables
    st.session_state.last_active_agent = "None"
    st.session_state.size_choice = 3
    st.session_state.target_duration = None
    st.session_state.previous_settings = {}
    st.session_state.planner_summary = ""

    st.session_state.video_session_id = ""
    st.session_state.video_filename = "video.mp4"
    st.session_state.uploader_key += 1
    st.rerun()

st.sidebar.markdown("***")
st.sidebar.caption(
    "**Studio Tips:**\n"
    '• *"Help me brainstorm a video..."* → Planner Agent\n'
    '• *"Read this script in a sweet voice"* → Voice Agent\n'
    '• *"Add a massive cinematic explosion"* → SFX Agent\n'
    '• *"Generate a portrait image of..."* → Image Agent\n'
    '• *"Add soft subtitles at top"* → Subtitle Agent'
)

# =========================================================
# 💬 CHAT UI
# =========================================================

# Display chat history
for entry in st.session_state.chat_history:
    with st.chat_message("user"):
        st.write(entry["prompt"])
        if entry.get("has_video"):
            icon = "📎" if entry.get("uploaded_now") else "📎 ↩"
            st.caption(f"{icon} {entry['video_name']}")

    with st.chat_message("assistant"):
        st.write(entry["reasoning"])

        # Handle Audio (Voice, SFX, Music)
        if entry.get("media_type") == "audio" and entry.get("media_data"):
            audio_bytes = base64.b64decode(entry["media_data"])
            st.audio(audio_bytes, format="audio/wav")
            st.download_button(
                "⬇️ Download Audio",
                data=audio_bytes,
                file_name="generated_audio.wav",
                mime="audio/wav",
                key=f"dl_audio_{entry['id']}",
            )

        # Handle Images
        elif entry.get("media_type") == "image" and entry.get("media_data"):
            image_bytes = base64.b64decode(entry["media_data"])
            st.image(image_bytes, use_container_width=True)
            st.download_button(
                "⬇️ Download Image",
                data=image_bytes,
                file_name="generated_image.jpg",
                mime="image/jpeg",
                key=f"dl_image_{entry['id']}",
            )

        # Handle Video (Generated or Subtitled)
        elif entry.get("media_type") == "video" and entry.get("media_data"):
            video_bytes = base64.b64decode(entry["media_data"])
            st.video(video_bytes)
            name, ext = os.path.splitext(entry.get("video_name", "video.mp4"))
            st.download_button(
                "⬇️ Download Video",
                data=video_bytes,
                file_name=f"{name}_output{ext}",
                mime="video/mp4",
                key=f"dl_video_{entry['id']}",
            )

# CSS to overlay the plus button inside the chat input on the left
d = chr(45)
css_styles = f"""
<style>
div[data{d}testid="stPopover"] {{
    position: fixed;
    bottom: 19px;
    z{d}index: 999;
    width: auto !important;
}}
div[data{d}testid="stPopover"] > div:first{d}child {{
    width: auto !important;
}}
div[data{d}testid="stPopover"] button[data{d}testid="stPopoverButton"] {{
    background: transparent !important;
    border: none !important;
    box{d}shadow: none !important;
    font{d}size: 1.2rem;
    padding: 2px 6px !important;
    min{d}width: 0 !important;
    width: auto !important;
    line{d}height: 1;
}}
div[data{d}testid="stChatInput"] textarea {{
    padding{d}left: 40px !important;
}}
div[data{d}testid="stChatInput"] div[data{d}testid="stChatInputTextArea"] p {{
    padding{d}left: 40px !important;
}}
</style>
"""
st.markdown(css_styles, unsafe_allow_html=True)

# Plus popover CSS positions it inside the chat input
with st.popover("➕"):
    uploaded_file = st.file_uploader(
        "Attach a video",
        type=["mp4", "mov", "avi", "mkv"],
        key=f"video_uploader_{st.session_state.uploader_key}",
    )

# Show attachment indicator above chat input
if uploaded_file is not None:
    st.caption(f"📎 **{uploaded_file.name}** ready to send")
elif st.session_state.video_session_id:
    st.caption(
        f"📎 **{st.session_state.video_filename}** in memory — subtitle follow ups will reuse this video"
    )

# Chat input
prompt = st.chat_input("Ask anything or generate media")
if prompt:
    video_attached = uploaded_file is not None

    with st.chat_message("user"):
        st.write(prompt)
        if video_attached:
            st.caption(f"📎 {uploaded_file.name}")
    uploaded_now = video_attached

    with st.chat_message("assistant"):
        status_box = st.status("Processing...")
        try:
            if video_attached:
                up_resp = requests.post(
                    UPLOAD_URL,
                    files={"file": (uploaded_file.name, uploaded_file.getvalue())},
                    timeout=120,
                )
                up_resp.raise_for_status()
                up_data = up_resp.json()
                st.session_state.video_session_id = up_data["session_id"]
                st.session_state.video_filename = up_data["filename"]

            history_len = len(st.session_state.chat_history)
            start_index = history_len.__sub__(6) if history_len > 6 else 0
            recent_history = st.session_state.chat_history[start_index:]

            chat_context_payload = []
            for past_msg in recent_history:
                chat_context_payload.append(
                    {"role": "user", "content": past_msg["prompt"]}
                )
                chat_context_payload.append(
                    {"role": "assistant", "content": past_msg["reasoning"]}
                )

            payload = {
                "input": prompt,
                "chat_context": chat_context_payload,
                "planner_summary": st.session_state.planner_summary,
                "last_active_agent": st.session_state.last_active_agent,
                "previous_music": st.session_state.music_context,
                "previous_image": st.session_state.image_context,
                "previous_voice": st.session_state.voice_context,
                "previous_sfx": st.session_state.sfx_context,
                "previous_video": st.session_state.video_context,
                "size_choice": st.session_state.size_choice,
                "target_duration": st.session_state.target_duration,
                "previous_settings": st.session_state.previous_settings,
            }
            if st.session_state.video_session_id:
                payload["session_id"] = st.session_state.video_session_id

            has_session = bool(payload.get("session_id"))
            video_name_for_entry = (
                uploaded_file.name
                if video_attached
                else st.session_state.video_filename
            )

            resp = requests.post(API_URL, json=payload, timeout=600, stream=True)

            if resp.status_code == 200:
                final_data = {}

                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line.decode("utf8"))
                        if chunk["type"] == "status":
                            status_box.update(label=chunk["message"])
                        elif chunk["type"] == "error":
                            status_box.update(label="Server Error", state="error")
                            st.error(chunk["message"])
                        elif chunk["type"] == "final":
                            final_data = chunk["data"]
                            status_box.update(label="Task Complete!", state="complete")

                if final_data:
                    data = final_data
                    media_data = data.get("media_data")
                    media_type = data.get("media_type")
                    reasoning = data.get("reasoning", "")

                    st.session_state.music_context = data.get(
                        "refined_music", st.session_state.music_context
                    )
                    st.session_state.image_context = data.get(
                        "refined_image", st.session_state.image_context
                    )
                    st.session_state.voice_context = data.get(
                        "refined_voice", st.session_state.voice_context
                    )
                    st.session_state.sfx_context = data.get(
                        "refined_sfx", st.session_state.sfx_context
                    )
                    st.session_state.video_context = data.get(
                        "refined_video", st.session_state.video_context
                    )

                    st.session_state.last_active_agent = data.get(
                        "last_active_agent", st.session_state.last_active_agent
                    )
                    st.session_state.size_choice = data.get(
                        "size_choice", st.session_state.size_choice
                    )
                    st.session_state.target_duration = data.get(
                        "target_duration", st.session_state.target_duration
                    )
                    st.session_state.previous_settings = data.get(
                        "previous_settings", st.session_state.previous_settings
                    )
                    st.session_state.planner_summary = data.get(
                        "planner_summary", st.session_state.planner_summary
                    )

                    st.session_state.video_session_id = data.get("session_id", "")
                    if not st.session_state.video_session_id:
                        st.session_state.video_filename = "video.mp4"

                    st.write(reasoning)

                    entry = {
                        "id": len(st.session_state.chat_history),
                        "prompt": prompt,
                        "reasoning": reasoning,
                        "media_data": media_data,
                        "media_type": media_type,
                        "has_video": video_attached or has_session,
                        "uploaded_now": video_attached,
                        "video_name": video_name_for_entry,
                    }

                    if media_type == "audio" and media_data:
                        st.audio(base64.b64decode(media_data), format="audio/wav")
                    elif media_type == "image" and media_data:
                        st.image(base64.b64decode(media_data), use_container_width=True)
                    elif media_type == "video" and media_data:
                        st.video(base64.b64decode(media_data))

                    st.session_state.chat_history.append(entry)

                    if video_attached:
                        st.session_state.uploader_key += 1
                        st.rerun()

            else:
                status_box.update(label="Failed to connect", state="error")
                st.error(f"Server Error: {resp.status_code}")

        except requests.exceptions.ConnectionError:
            status_box.update(label="Connection Error", state="error")
            st.error("Cannot connect to the backend. Is it running?")
        except Exception as e:
            status_box.update(label="System Error", state="error")
            st.error(f"Error: {e}")
