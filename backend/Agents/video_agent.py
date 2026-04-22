import requests
import base64
from typing import TypedDict

from langgraph.graph import StateGraph
from config import Settings
from prompts.video.extract_keyword_prompt import extract_keyword_prompt


class AgentState(TypedDict, total=False):
    original: str
    video_b64: str
    keyword: str
    previous: str


class Pixel_Video_Agent:
    def __init__(self, strict_llm) -> None:
        self.api_key = Settings.PEXELS_KEY
        self.llm = strict_llm

    def extract_keyword_node(self, state: AgentState) -> AgentState:
        prompt = extract_keyword_prompt(
            str(state.get("original")), state.get("previous", "")
        )
        print("@@ Extract Keyword Prompt @@\n")
        print(prompt)
        print("@@ Extract Keyword Prompt @@\n")

        response = self.llm.invoke(prompt)

        # Scrubbing the response to keep it perfectly clean
        keyword = str(response.content).strip()
        keyword = (
            keyword.replace('"', "").replace("Keywords:", "").replace("Keywords", "")
        )

        print(f"@@ Extracted Keywords: {keyword} @@")
        state["keyword"] = keyword
        return state

    def fetch_video_node(self, state: AgentState) -> AgentState:
        keyword = state.get("keyword", "nature")
        print(f"@@ Fetching B Roll for: {keyword} @@")

        url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=1"
        headers = {"Authorization": self.api_key}

        try:
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                if data.get("videos") and len(data["videos"]) > 0:

                    # Pexels returns multiple resolutions. We grab the first available file link.
                    video_files = data["videos"][0]["video_files"]
                    video_url = video_files[0]["link"]

                    # Download the actual MP4 bytes
                    vid_res = requests.get(video_url)
                    if vid_res.status_code == 200:
                        # We use ascii decoding here which is safe for base64 strings
                        state["video_b64"] = base64.b64encode(vid_res.content).decode(
                            "ascii"
                        )
        except Exception as e:
            print(f"Error fetching video: {str(e)}")

        return state

    def get_app(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("extractor", self.extract_keyword_node)
        workflow.add_node("fetcher", self.fetch_video_node)

        workflow.add_edge("extractor", "fetcher")

        workflow.set_entry_point("extractor")
        workflow.set_finish_point("fetcher")

        return workflow.compile()
