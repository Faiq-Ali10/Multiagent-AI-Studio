import re
import os
import sys
import io
import wave
from typing import TypedDict

from langgraph.graph import StateGraph

# Force Python to look at the main backend folder BEFORE importing local packages
root_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_folder not in sys.path:
    sys.path.insert(0, root_folder)

from prompts.sfx.sfx_parser_prompt import sfx_parser_prompt


class AgentState(TypedDict, total=False):
    original: str
    previous: str
    keyword: str
    audio_b64: str
    target_duration: int
    duration: int


class SFXAgent:
    def __init__(self, strict_llm) -> None:
        self.llm = strict_llm

    @staticmethod
    def _fallback_keyword(original: str, previous: str) -> str:
        combined = f"{original} {previous}".strip().lower()
        if not combined:
            return "heavy footsteps"

        cleaned = re.sub(r"[^a-z0-9\s-]", " ", combined)
        words = [w for w in cleaned.split() if len(w) > 2]
        if not words:
            return "heavy footsteps"

        return " ".join(words[:4])

    @staticmethod
    def _extract_duration_seconds(text: str):
        if not text:
            return None

        # Numeric seconds: 7s, 7 sec, 7 seconds
        sec_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:s|sec|secs|second|seconds)\b", text, re.I
        )
        if sec_match:
            try:
                return int(round(float(sec_match.group(1))))
            except ValueError:
                pass

        # Numeric minutes: 2m, 2 min, 2 minutes
        min_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:m|min|mins|minute|minutes)\b", text, re.I
        )
        if min_match:
            try:
                return int(round(float(min_match.group(1)) * 60))
            except ValueError:
                pass

        # Word numbers before units: "ten seconds", "seven sec", "two minutes"
        word_to_num = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
            "eleven": 11,
            "twelve": 12,
            "thirteen": 13,
            "fourteen": 14,
            "fifteen": 15,
            "sixteen": 16,
            "seventeen": 17,
            "eighteen": 18,
            "nineteen": 19,
            "twenty": 20,
            "thirty": 30,
        }

        word_match = re.search(
            r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty)\s*(?:s|sec|secs|second|seconds|m|min|mins|minute|minutes)\b",
            text,
            re.I,
        )
        if word_match:
            num = word_to_num.get(word_match.group(1).lower())
            if num is None:
                return None
            if re.search(
                r"\b(?:m|min|mins|minute|minutes)\b", word_match.group(0), re.I
            ):
                return num * 60
            return num

        return None

    @staticmethod
    def _enforce_wav_duration(audio_bytes: bytes, target_seconds: int):
        """Return WAV bytes normalized to target length by trimming or looping."""
        try:
            src_buf = io.BytesIO(audio_bytes)
            with wave.open(src_buf, "rb") as src:
                channels = src.getnchannels()
                sampwidth = src.getsampwidth()
                framerate = src.getframerate()
                nframes = src.getnframes()
                frames = src.readframes(nframes)

            if framerate <= 0 or channels <= 0 or sampwidth <= 0:
                return audio_bytes, None

            bytes_per_frame = channels * sampwidth
            target_frames = int(max(1, target_seconds) * framerate)

            if nframes <= 0 or bytes_per_frame <= 0:
                return audio_bytes, None

            if nframes > target_frames:
                frames = frames[: target_frames * bytes_per_frame]
            elif nframes < target_frames:
                repeats = (target_frames + nframes - 1) // nframes
                frames = (frames * repeats)[: target_frames * bytes_per_frame]

            out_buf = io.BytesIO()
            with wave.open(out_buf, "wb") as dst:
                dst.setnchannels(channels)
                dst.setsampwidth(sampwidth)
                dst.setframerate(framerate)
                dst.writeframes(frames)

            return out_buf.getvalue(), round(target_frames / float(framerate), 3)
        except Exception as e:
            print(f"@@ WAV Parsing Error: {str(e)} @@")
            return None, None

    def sfx_parser_node(self, state: AgentState) -> AgentState:
        original = str(state.get("original") or "")
        previous = str(state.get("previous") or "")

        prompt = sfx_parser_prompt(original, previous)

        if self.llm is not None:
            response = self.llm.invoke(prompt)
            keyword = str(response.content).strip().replace('"', "")
        else:
            keyword = self._fallback_keyword(original, previous)

        if not keyword:
            keyword = "heavy footsteps"

        state["keyword"] = keyword
        return state

    def generate_sfx_node(self, state: AgentState) -> AgentState:
        from gradio_client import Client
        import base64

        keyword = state.get("keyword", "heavy footsteps")

        # Normalize incoming duration from supervisor/user. TangoFlux max is 30s.
        raw_duration = state.get("target_duration")
        clip_length = None
        try:
            if raw_duration is not None:
                clip_length = int(float(raw_duration))
        except (TypeError, ValueError):
            clip_length = None

        # Defensive fallback in case target_duration was missing from state.
        if clip_length is None:
            clip_length = self._extract_duration_seconds(
                str(state.get("original") or "")
            )

        if clip_length is None:
            clip_length = self._extract_duration_seconds(str(keyword))

        if clip_length is None or clip_length <= 0:
            clip_length = 5

        # Ensure it never asks for more than 30 seconds to prevent a crash
        if clip_length > 30:
            clip_length = 30

        print(f"@@ Generating {clip_length} seconds of SFX for: {keyword} @@")

        hyphen = chr(45)
        space_name = f"declare{hyphen}lab/TangoFlux"

        audio_b64 = None

        try:
            client = Client(space_name)

            # Pass arguments positionally! (prompt, duration, steps, guidance_scale)
            # This guarantees Gradio will not silently ignore your clip_length
            result_audio_path = client.predict(
                keyword,  # prompt
                50,  # steps
                clip_length,  # duration
                3,  # guidance_scale
                api_name="/predict",
            )

            with open(result_audio_path, "rb") as audio_file:
                audio_bytes = audio_file.read()

                audio_bytes, fixed_seconds = self._enforce_wav_duration(
                    audio_bytes, clip_length
                )

                # Check if the bytes survived the duration enforcer
                if audio_bytes is not None:
                    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
                    if fixed_seconds is not None:
                        print(
                            f"@@ SFX normalized output length: {fixed_seconds} seconds @@"
                        )
                    print("@@ SFX Generated Successfully! @@")
                else:
                    print("@@ SFX Failed: Received corrupted file from server @@")
                    audio_b64 = None

        except Exception as e:
            print(f"SFX generation error: {str(e)}")

        state["audio_b64"] = audio_b64
        state["duration"] = clip_length
        return state

    def get_app(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("parser", self.sfx_parser_node)
        workflow.add_node("generator", self.generate_sfx_node)

        workflow.add_edge("parser", "generator")

        workflow.set_entry_point("parser")
        workflow.set_finish_point("generator")

        return workflow.compile()


if __name__ == "__main__":
    import base64

    print("Initializing SFX Agent...")

    agent = SFXAgent()
    app = agent.get_app()

    test_prompt = "make a sound of cows working on ground"
    print(f"Running Test: {test_prompt}")

    initial_state = {"original": test_prompt, "target_duration": 10}

    final_state = app.invoke(initial_state)
    audio_b64 = final_state.get("audio_b64")

    if audio_b64:
        output_path = "test_sfx.wav"
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(audio_b64))
        print(f"Success! SFX saved as {output_path} in your current folder!")
    else:
        print("Test failed. No SFX data returned.")
