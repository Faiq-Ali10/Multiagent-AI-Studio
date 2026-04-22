from typing import TypedDict
from langgraph.graph import StateGraph
import base64

# Import the utility function we created earlier
from utils.subtitle_utils import process_and_burn_subtitles, process_outline_subtitles

class SubtitleAgentState(TypedDict, total=False):
    video_b64: str
    original_filename: str
    subtitle_type: int       # Expects 1 for inline or 2 for outline
    position: str            # Expects top, bottom, center, etc.
    subtitled_video_b64: str
    message: str

class SubtitleAgent():
    def __init__(self) -> None:
        pass

    def router_node(self, state: SubtitleAgentState) -> SubtitleAgentState:
        # Reads the requested subtitle type
        sub_type = state.get("subtitle_type", 1)
        
        print("@@Subtitle Router@@\n")
        print(f"Routing request for type: {sub_type}")
        print("@@Subtitle Router@@\n")
        
        return state

    def inline_node(self, state: SubtitleAgentState) -> SubtitleAgentState:
        print("@@Processing Inline Subtitles@@\n")
        
        video_b64 = state.get("video_b64", "")
        filename = state.get("original_filename", "video.mp4")
        position = state.get("position", "bottom")
        
        try:
            video_bytes = base64.b64decode(video_b64)
            result_b64 = process_and_burn_subtitles(video_bytes, filename, position)
            
            state["subtitled_video_b64"] = result_b64
            state["message"] = "Inline subtitles successfully added."
            
        except Exception as e:
            print("Error: " + str(e))
            state["message"] = str(e)
            
        return state

    def outline_node(self, state: SubtitleAgentState) -> SubtitleAgentState:
        print("@@Processing Outline Subtitles@@\n")
        
        video_b64 = state.get("video_b64", "")
        filename = state.get("original_filename", "video.mp4")
        
        try:
            video_bytes = base64.b64decode(video_b64)
            result_b64 = process_outline_subtitles(video_bytes, filename)
            
            state["subtitled_video_b64"] = result_b64
            state["message"] = "Outline subtitles successfully attached."
            
        except Exception as e:
            print("Error: " + str(e))
            state["message"] = str(e)
            
        return state

    def get_app(self):
        workflow = StateGraph(SubtitleAgentState)
        
        # Add Nodes
        workflow.add_node("router", self.router_node)
        workflow.add_node("inline_processor", self.inline_node)
        workflow.add_node("outline_processor", self.outline_node)
        
        # Logic Check Function
        def check_subtitle_type(state):
            sub_type = state.get("subtitle_type", 1)
            if sub_type == 1:
                return "inline_processor"
            else:
                return "outline_processor"

        # Add Conditional Edges from the Router
        workflow.add_conditional_edges(
            "router",
            check_subtitle_type,
            {
                "inline_processor": "inline_processor",
                "outline_processor": "outline_processor",
            }
        )
        
        workflow.set_entry_point("router")
        
        # Finish points
        workflow.set_finish_point("inline_processor")
        workflow.set_finish_point("outline_processor")
        
        app = workflow.compile()
        
        return app