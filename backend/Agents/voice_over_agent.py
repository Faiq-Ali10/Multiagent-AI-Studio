import os
import sys
import json
import base64
import asyncio
from typing import TypedDict
import edge_tts
from langgraph.graph import StateGraph

# Force Python to look at the main backend folder BEFORE importing local packages
root_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_folder not in sys.path:
    sys.path.insert(0, root_folder)

from prompts.voice_over.voice_over_parser_prompt import voice_over_parser_prompt


class VoiceState(TypedDict, total=False):
    original: str
    transcript: str
    gender: str
    speed: str
    pitch: str
    voice_type: str
    audio_b64: str

    # Memory bank for sticky conversational sessions
    previous_transcript: str
    previous_settings: dict


class VoiceAgent:
    def __init__(self, strict_llm) -> None:
        self.llm = strict_llm

    def parse_voice_node(self, state: VoiceState) -> VoiceState:
        original = str(state.get("original") or "")

        # Safely pull memory for conversational continuity
        previous_transcript = str(state.get("previous_transcript") or "")
        previous_settings = state.get("previous_settings") or {}

        # Build context string so Llama-3 knows what was decided in the last turn
        previous_context = ""
        if previous_transcript or previous_settings:
            previous_context = (
                f"Script: {previous_transcript} | Profile: {previous_settings}"
            )

        # Get the optimized prompt that uses Edge-TTS domains directly
        prompt = voice_over_parser_prompt(
            original, previous_context if previous_context else None
        )

        print("@@ Extracting Voice Settings from Llama-3 @@")

        try:
            if self.llm is not None:
                response = self.llm.invoke(prompt)

                # Clean markdown and parse JSON
                clean_json = (
                    str(response.content)
                    .strip()
                    .replace("```json", "")
                    .replace("```", "")
                )
                settings = json.loads(clean_json)

                # Map extracted JSON directly to State
                state["transcript"] = settings.get("transcript", "")
                state["gender"] = settings.get("gender", "Female")
                state["speed"] = settings.get("speed", "+0%")
                state["pitch"] = settings.get("pitch", "+0Hz")
                state["voice_type"] = settings.get("voice_type", "en-US-AriaNeural")
            else:
                raise Exception("LLM Object is None")

        except Exception as e:
            print(f"@@ Parsing Error: {str(e)} @@")
            state["transcript"] = original
            state["gender"] = "Female"
            state["speed"] = "+0%"
            state["pitch"] = "+0Hz"
            state["voice_type"] = "en-US-AriaNeural"

        # Update memory for the next conversational turn
        state["previous_transcript"] = state["transcript"]
        state["previous_settings"] = {
            "gender": state["gender"],
            "speed": state["speed"],
            "pitch": state["pitch"],
            "voice_type": state["voice_type"],
        }

        print(f"@@ Target Script: {state['transcript'][:50]}... @@")
        print(
            f"@@ Target Voice: {state['voice_type']} (Speed: {state['speed']}, Pitch: {state['pitch']}) @@"
        )
        return state

    def generate_voice_node(self, state: VoiceState) -> VoiceState:
        import threading  # Import standard threading to isolate the event loop

        # These are now pre-formatted by the LLM for Edge-TTS!
        transcript = state.get("transcript", "")
        voice_name = state.get("voice_type", "en-US-AriaNeural")
        rate_str = state.get("speed", "+0%")
        pitch_str = state.get("pitch", "+0Hz")

        print(f"@@ Synthesizing Speech via Edge-TTS: {voice_name} @@")

        async def run_tts():
            try:
                communicate = edge_tts.Communicate(
                    text=transcript, voice=voice_name, rate=rate_str, pitch=pitch_str
                )

                temp_path = "temp_voice.mp3"
                await communicate.save(temp_path)

                with open(temp_path, "rb") as audio_file:
                    audio_bytes = audio_file.read()
                    state["audio_b64"] = base64.b64encode(audio_bytes).decode("ascii")

                # Housekeeping: Remove local file after encoding to memory
                if os.path.exists(temp_path):
                    os.remove(temp_path)

                print("@@ Audio Generated and Encoded to Base64 @@")

            except Exception as e:
                print(f"@@ TTS Engine Error: {str(e)} @@")

        # THE FIX: Isolate the async execution in a new thread
        # This prevents the "asyncio.run() cannot be called from a running event loop" error in FastAPI
        def thread_worker():
            asyncio.run(run_tts())

        tts_thread = threading.Thread(target=thread_worker)
        tts_thread.start()
        tts_thread.join()  # Wait for the thread to finish before returning the state

        return state

    def get_app(self):
        workflow = StateGraph(VoiceState)

        workflow.add_node("parser", self.parse_voice_node)
        workflow.add_node("generator", self.generate_voice_node)

        workflow.add_edge("parser", "generator")

        workflow.set_entry_point("parser")
        workflow.set_finish_point("generator")

        return workflow.compile()


if __name__ == "__main__":
    agent = VoiceAgent()
    app = agent.get_app()

    # Initial Test
    test_prompt = "Say 'Hello Faiq, your agent is ready,  how can i help you you can ask me anything' in a sweet female voice"
    print(f"\n--- Turn 1: {test_prompt} ---")
    state_1 = app.invoke({"original": test_prompt})

    # Follow-up Test (Sticky Memory Check)
    follow_up = "Now add 'Let's build something amazing' at the end"
    print(f"\n--- Turn 2: {follow_up} ---")
    # We pass the full state back to maintain memory
    state_2 = app.invoke(
        {
            "original": follow_up,
            "previous_transcript": state_1.get("previous_transcript"),
            "previous_settings": state_1.get("previous_settings"),
        }
    )

    # Save final result
    audio_data = state_2.get("audio_b64")
    if audio_data:
        with open("final_output.mp3", "wb") as f:
            f.write(base64.b64decode(audio_data))
        print("\nSuccess! Final voice with memory saved as final_output.mp3")
