from typing import TypedDict
from langgraph.graph import StateGraph

from prompts.image.refine_prompt import image_refine_prompt

# Import Models
from models.image_gen import generate_image_data


class AgentState(TypedDict, total=False):
    original: str
    refined: str
    image_b64: str  # Stores Base64 string instead of bytes/url
    previous: str
    size_choice: int  # Specific to images


class ImageAgent:
    def __init__(self, creative_llm) -> None:
        # Initialize LLM (we create new instances in nodes, but good for setup)
        self.llm = creative_llm
        return None

    def refiner_node(self, state: AgentState) -> AgentState:
        # 1. Generate Prompt
        prompt = image_refine_prompt(
            str(state.get("original")), str(state.get("previous"))
        )

        print("@@Img Refiner@@\n")
        print(prompt)
        print("@@Img Refiner@@\n")

        response = self.llm.invoke(prompt)

        print("@@Img Refiner_response@@\n")
        print(response.content)
        print("@@Img Refiner_response@@\n")

        # 3. Update State
        state["refined"] = str(response.content)
        return state

    def generate_image_node(self, state: AgentState) -> AgentState:
        # Get inputs
        prompt = str(state.get("refined"))
        choice = state.get("size_choice", 3)  # Default to 3 if missing

        # Call the Image Generator
        # Returns Base64 string
        image_data = generate_image_data(prompt, choice)

        # Update State
        state["image_b64"] = image_data
        return state

    def get_app(self):
        workflow = StateGraph(AgentState)

        # Add Nodes
        workflow.add_node("refiner", self.refiner_node)
        workflow.add_node("generator", self.generate_image_node)

        workflow.add_edge("refiner", "generator")

        workflow.set_entry_point("refiner")
        workflow.set_finish_point("generator")

        app = workflow.compile()

        return app
