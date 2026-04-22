from typing import TypedDict
from prompts.music.refine_prompt import refine_prompt
from models.music import generate_music
from langgraph.graph import StateGraph


class AgentState(TypedDict, total=False):
    original: str
    refined: str
    music: bytes
    previous: str
    duration: int


class MusicAgent:
    def __init__(self, creative_llm) -> None:
        self.llm = creative_llm
        return None

    def refiner_node(self, state: AgentState) -> AgentState:
        prompt = refine_prompt(str(state.get("original")), str(state.get("previous")))
        print("@@refiner@@\n")
        print(prompt)
        print("@@refiner@@\n")
        response = self.llm.invoke(prompt)
        print("@@refiner_response@@\n")
        print(response.content)
        print("@@refiner_response@@\n")

        state["refined"] = str(response.content)
        return state

    def generate_music_node(self, state: AgentState) -> AgentState:
        # 1 second is roughly equal to 51 tokens
        max_new_tokens = state.get("duration", 0) * 51
        if max_new_tokens == 0:
            max_new_tokens = 512  # Default to 512 tokens if no duration specified
        music = generate_music(str(state.get("refined")), max_new_tokens=max_new_tokens)

        state["music"] = music
        return state

    def get_app(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("refiner", self.refiner_node)
        workflow.add_node("generator", self.generate_music_node)

        workflow.add_edge("refiner", "generator")

        workflow.set_entry_point("refiner")
        workflow.set_finish_point("generator")

        app = workflow.compile()

        return app
