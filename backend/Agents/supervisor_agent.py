import json
import re
from typing import Sequence
from pydantic import BaseModel
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage

from models.llm import LLM_Model
from config import Settings
from prompts.supervisor.supervisor_prompt import supervisor_system_prompt

from Agents.music_agent import MusicAgent
from Agents.image_agent import ImageAgent
from Agents.subtitle_agent import SubtitleAgent
from Agents.planner_agent import PlannerAgent
from Agents.voice_over_agent import VoiceAgent
from Agents.sfx_agent import SFXAgent
from Agents.video_agent import Pixel_Video_Agent


class SupervisorOutput(BaseModel):
    next: str
    reasoning: str


class AgentState(dict):
    messages: Sequence[BaseMessage]
    summary: str = ""
    next: str
    reasoning: str
    step_count: int
    media_data: bytes = None
    media_type: str = None
    video_b64: str = None
    original_filename: str = None
    subtitle_type: int = None
    position: str = None
    safety_violation: bool = False

    # --- MEMORY CONFIGURATIONS ---
    size_choice: int = None  # Image Agent memory
    sfx_target_duration: int = None  # SFX Agent memory
    previous_settings: dict = None  # Voice Agent memory
    music_duration: int = None  # Music Agent memory

    # --- PROMPT REFINEMENT MEMORY ---
    last_music_refined: str = None
    last_image_refined: str = None
    last_voice_refined: str = None
    last_sfx_refined: str = None
    last_video_refined: str = None
    last_active_agent: str = None


class ContentSupervisor:
    def __init__(self):
        self.strict_llm = None
        self.creative_llm = None
        try:
            self.strict_llm = LLM_Model(0.1, api_key=Settings.GROQ_API_KEY).get_model()
            self.creative_llm = LLM_Model(
                0.5, api_key=Settings.GROQ_API_KEY
            ).get_model()
        except Exception as e:
            print(f"@@ LLM unavailable: {e} @@")

        self.llm = self.strict_llm

        self.planner_engine = PlannerAgent(self.creative_llm).get_app()
        self.voice_engine = VoiceAgent(self.strict_llm).get_app()
        self.sfx_engine = SFXAgent(self.strict_llm).get_app()
        self.music_engine = MusicAgent(self.creative_llm).get_app()
        self.image_engine = ImageAgent(self.creative_llm).get_app()
        self.video_engine = Pixel_Video_Agent(self.strict_llm).get_app()
        self.subtitle_engine = SubtitleAgent().get_app()

        d = chr(45)
        self.model_name = "llama3" + d + "8b" + d + "8192"

    def _limit_msgs(self, msg_list):
        """Helper method to ensure we only keep the last 6 messages"""
        total = len(msg_list)
        if total > 6:
            start_index = total.__sub__(6)
            return msg_list[start_index:]
        return msg_list

    @staticmethod
    def _extract_duration_seconds(text: str):
        if not text:
            return None

        value = None

        # Examples matched: "10s", "10 sec", "10 seconds"
        sec_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:s|sec|secs|second|seconds)\b", text, re.I
        )
        if sec_match:
            try:
                value = int(round(float(sec_match.group(1))))
            except ValueError:
                value = None

        # Examples matched: "2 min", "2 minutes"
        if value is None:
            min_match = re.search(
                r"(\d+(?:\.\d+)?)\s*(?:m|min|mins|minute|minutes)\b", text, re.I
            )
            if min_match:
                try:
                    value = int(round(float(min_match.group(1)) * 60))
                except ValueError:
                    value = None

        if value is None:
            return None

        if value < 1:
            return 1
        if value > 30:
            return 30
        return value

    @staticmethod
    def _coerce_int(value, default=None):
        try:
            if value is None:
                return default
            return int(value)
        except (TypeError, ValueError):
            return default

    def supervisor_node(self, state: AgentState) -> dict:
        try:
            step = state.get("step_count", 0) + 1
            messages = state.get("messages", [])

            last_message = "No input"
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    last_message = msg.content
                    break

            has_agent_response = any(
                isinstance(msg, AIMessage)
                and msg.name
                in (
                    "planner_node",
                    "voice_over_node",
                    "sfx_node",
                    "music_node",
                    "image_node",
                    "video_node",
                    "subtitle_node",
                )
                for msg in messages
            )

            if has_agent_response:
                return {"next": END, "reasoning": "Task complete."}

            # 1. Gather the basic state
            last_active_agent = state.get("last_active_agent") or "None"
            video_loaded = "Yes" if state.get("video_b64") else "No"

            # 2. Dynamically build the context list (Pruning the noise)
            contexts = []
            if state.get("last_music_refined"):
                contexts.append(f"Music: {state.get('last_music_refined')}")
            if state.get("last_image_refined"):
                contexts.append(f"Image: {state.get('last_image_refined')}")
            if state.get("last_voice_refined"):
                contexts.append(f"Voice: {state.get('last_voice_refined')}")
            if state.get("last_sfx_refined"):
                contexts.append(f"SFX: {state.get('last_sfx_refined')}")
            if state.get("last_video_refined"):
                contexts.append(f"Video: {state.get('last_video_refined')}")

            context_str = (
                "\n".join(contexts) if contexts else "No media contexts active."
            )

            # 1. Get the pure system instructions
            system_instructions = supervisor_system_prompt()

            # 2. Put the dynamic state and user input into the Human Message
            human_content = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT SESSION STATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Last Active Agent: {last_active_agent}
Video Loaded: {video_loaded}

[Active Contexts]
{context_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER INPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"{last_message}"
"""
            # 3. Pass them as an array so LLaMA-3 formats them perfectly
            messages_for_llm = [
                SystemMessage(content=system_instructions),
                HumanMessage(content=human_content),
            ]

            # 4. Invoke using the array
            response = self.llm.invoke(messages_for_llm)

            print("@@@ Supervisor Prompt @@@\n", flush=True)
            print(human_content, flush=True)
            print("@@@ Supervisor Prompt @@@\n", flush=True)

            response = self.llm.invoke(messages_for_llm)

            print("@@@ Supervisor Response @@@\n", flush=True)
            print(response.content, flush=True)
            print("@@@ Supervisor Response @@@\n", flush=True)

            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            content = content.replace("{{", "{").replace("}}", "}")

            parsed = {}
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group())
                except Exception:
                    try:
                        fixed = re.sub(r",\s*}", "}", match.group())
                        fixed = re.sub(r",\s*]", "]", fixed)
                        parsed = json.loads(fixed)
                    except Exception:
                        pass

            extracted_route = parsed.get("route") or parsed.get("next", "FINISH")
            next_step = extracted_route.upper()
            reasoning = parsed.get("reasoning", "").lower()

            if next_step == "FINISH" or step > 10:
                if (
                    "gibberish" in reasoning
                    or "nonsense" in reasoning
                    or "unclear" in reasoning
                ):
                    print("@@@ Trashing gibberish message from history @@@", flush=True)
                    clean_messages = list(state.get("messages", []))
                    if len(clean_messages) > 0:
                        clean_messages.pop()

                    return {
                        "next": END,
                        "reasoning": parsed.get(
                            "reasoning",
                            "Hmm, I didn't quite catch that. Could you clarify what you'd like to create?",
                        ),
                        "messages": self._limit_msgs(clean_messages),
                    }

                return {
                    "next": END,
                    "reasoning": parsed.get(
                        "reasoning", "Task complete or chat response."
                    ),
                }

            mapping = {
                "PLANNER": "planner_node",
                "VOICE_OVER": "voice_over_node",
                "SFX": "sfx_node",
                "MUSIC": "music_node",
                "IMAGE": "image_node",
                "VIDEO": "video_node",
                "SUBTITLE": "subtitle_node",
            }

            goto = mapping.get(next_step, END)

            extracted_size = parsed.get("size_choice", state.get("size_choice", 3))
            extracted_sub_type = parsed.get(
                "subtitle_type", state.get("subtitle_type", 1)
            )
            extracted_position = parsed.get("position", state.get("position", "bottom"))
            extracted_music_duration = self._coerce_int(
                parsed.get("music_duration", state.get("music_duration", 0)),
                state.get("music_duration", 0),
            )

            is_safety_violation = parsed.get("safety_violation", False)

            llm_sfx_duration = self._coerce_int(parsed.get("target_duration"), None)
            text_sfx_duration = self._extract_duration_seconds(str(last_message))
            extracted_sfx_duration = (
                text_sfx_duration
                if text_sfx_duration is not None
                else (
                    llm_sfx_duration
                    if llm_sfx_duration is not None
                    else state.get("sfx_target_duration")
                )
            )

            clear_state = {
                "next": goto,
                "reasoning": reasoning,
                "step_count": step,
                "media_data": None,
                "media_type": None,
                "size_choice": extracted_size,
                "subtitle_type": extracted_sub_type,
                "position": extracted_position,
                "music_duration": extracted_music_duration,
                "sfx_target_duration": extracted_sfx_duration,
                "safety_violation": is_safety_violation,
            }

            if goto in (
                "music_node",
                "image_node",
                "video_node",
                "voice_over_node",
                "sfx_node",
            ):
                clear_state["video_b64"] = None
                clear_state["original_filename"] = None

            return clear_state

        except Exception as e:
            print(f"Error in Supervisor: {str(e)}", flush=True)
            return {"next": END}

    def planner_node(self, state: AgentState) -> dict:
        print("@@@ ENTERING PLANNER AGENT @@@", flush=True)

        result = self.planner_engine.invoke(
            {
                "messages": state.get("messages", []),
                "planner_summary": state.get("planner_summary", ""),
                "safety_violation": state.get(
                    "safety_violation", False
                ),  # Pass the flag down!
            }
        )

        final_messages = result.get("messages", state.get("messages", []))
        new_summary = result.get("planner_summary", state.get("planner_summary", ""))

        return {
            "messages": self._limit_msgs(final_messages),
            "last_active_agent": "planner",
            "planner_summary": new_summary,
            "safety_violation": False,  # Reset the flag for the next turn
        }

    def voice_over_node(self, state: AgentState) -> dict:
        print("@@@ ENTERING VOICE OVER AGENT @@@", flush=True)

        user_input = ""
        if state.get("messages"):
            user_input = list(reversed(state["messages"]))[0].content

        result = self.voice_engine.invoke(
            {
                "original": user_input,
                "previous_transcript": state.get("last_voice_refined"),
                "previous_settings": state.get("previous_settings"),
            }
        )

        new_messages = state.get("messages", []) + [
            AIMessage(
                content="Voiceover generated successfully!",
                name="voice_over_node",
            )
        ]

        return {
            "messages": self._limit_msgs(new_messages),
            "media_data": result.get("audio_b64"),
            "media_type": "audio",
            "last_voice_refined": result.get("transcript"),
            "previous_settings": result.get("settings", state.get("previous_settings")),
            "last_active_agent": "voice_over",
        }

    def sfx_node(self, state: AgentState) -> dict:
        print("@@@ ENTERING SFX AGENT @@@", flush=True)

        user_input = ""
        if state.get("messages"):
            user_input = list(reversed(state["messages"]))[0].content

        resolved_target_duration = state.get("sfx_target_duration")
        if resolved_target_duration is None:
            resolved_target_duration = state.get("target_duration")
        if resolved_target_duration is None:
            resolved_target_duration = self._extract_duration_seconds(str(user_input))

        result = self.sfx_engine.invoke(
            {
                "original": user_input,
                "previous": state.get("last_sfx_refined"),
                "target_duration": resolved_target_duration,
            }
        )

        new_messages = state.get("messages", []) + [
            AIMessage(content="Sound effect generated successfully!", name="sfx_node")
        ]

        return {
            "messages": self._limit_msgs(new_messages),
            "media_data": result.get("audio_b64"),
            "media_type": "audio",
            "last_sfx_refined": result.get("keyword"),
            "sfx_target_duration": result.get("duration", resolved_target_duration),
            "target_duration": result.get("duration", resolved_target_duration),
            "last_active_agent": "sfx",
        }

    def video_node(self, state: AgentState) -> dict:
        print("@@@ ENTERING VIDEO AGENT @@@", flush=True)

        user_input = ""
        if state.get("messages"):
            user_input = list(reversed(state["messages"]))[0].content

        previous = state.get("last_video_refined") or ""
        result = self.video_engine.invoke(
            {"original": user_input, "previous": previous}
        )

        new_messages = state.get("messages", []) + [
            AIMessage(content="Video clip generated successfully!", name="video_node")
        ]

        return {
            "messages": self._limit_msgs(new_messages),
            "media_data": result.get("video_b64"),
            "media_type": "video",
            "last_video_refined": result.get("keyword"),
            "last_active_agent": "video",
        }

    def music_node(self, state: AgentState) -> dict:
        print("@@@ ENTERING MUSIC AGENT @@@", flush=True)

        user_input = ""
        if state.get("messages"):
            user_input = list(reversed(state["messages"]))[0].content

        previous = state.get("last_music_refined") or ""
        result = self.music_engine.invoke(
            {
                "original": user_input,
                "previous": previous,
                "duration": state.get("music_duration") or 0,
            }
        )
        refined = result.get("refined") or previous

        new_messages = state.get("messages", []) + [
            AIMessage(content="Music generation complete!", name="music_node")
        ]

        return {
            "messages": self._limit_msgs(new_messages),
            "media_data": result.get("music"),
            "media_type": "audio",
            "last_music_refined": refined,
            "last_active_agent": "music",
        }

    def image_node(self, state: AgentState) -> dict:
        print("@@@ ENTERING IMAGE AGENT @@@", flush=True)

        user_input = ""
        if state.get("messages"):
            user_input = list(reversed(state["messages"]))[0].content

        previous = state.get("last_image_refined") or ""
        size_choice = state.get("size_choice") or 3
        result = self.image_engine.invoke(
            {"original": user_input, "previous": previous, "size_choice": size_choice}
        )

        new_messages = state.get("messages", []) + [
            AIMessage(content="Image created successfully.", name="image_node")
        ]

        return {
            "messages": self._limit_msgs(new_messages),
            "media_data": result.get("image_b64"),
            "media_type": "image",
            "last_image_refined": result.get("refined") or previous,
            "size_choice": result.get("size_choice", size_choice),
            "last_active_agent": "image",
        }

    def subtitle_node(self, state: AgentState) -> dict:
        print("@@@ ENTERING SUBTITLE AGENT @@@", flush=True)

        video_b64 = state.get("video_b64", "")
        original_filename = state.get("original_filename", "video.mp4")
        subtitle_type = state.get("subtitle_type", 1)
        position = state.get("position", "bottom")

        result = self.subtitle_engine.invoke(
            {
                "video_b64": video_b64,
                "original_filename": original_filename,
                "subtitle_type": subtitle_type,
                "position": position,
            }
        )

        new_messages = state.get("messages", []) + [
            AIMessage(
                content=result.get("message", "Subtitles processed."),
                name="subtitle_node",
            )
        ]

        return {
            "messages": self._limit_msgs(new_messages),
            "media_data": result.get("subtitled_video_b64"),
            "media_type": "video",
            "last_active_agent": "subtitle",
        }

    def get_app(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("supervisor", self.supervisor_node)
        workflow.add_node("planner_node", self.planner_node)
        workflow.add_node("voice_over_node", self.voice_over_node)
        workflow.add_node("sfx_node", self.sfx_node)
        workflow.add_node("music_node", self.music_node)
        workflow.add_node("image_node", self.image_node)
        workflow.add_node("video_node", self.video_node)
        workflow.add_node("subtitle_node", self.subtitle_node)

        workflow.set_entry_point("supervisor")

        workflow.add_conditional_edges(
            "supervisor", lambda state: state.get("next", END)
        )

        workflow.add_edge("planner_node", "supervisor")
        workflow.add_edge("voice_over_node", "supervisor")
        workflow.add_edge("sfx_node", "supervisor")
        workflow.add_edge("music_node", "supervisor")
        workflow.add_edge("image_node", "supervisor")
        workflow.add_edge("video_node", "supervisor")
        workflow.add_edge("subtitle_node", "supervisor")

        return workflow.compile()
