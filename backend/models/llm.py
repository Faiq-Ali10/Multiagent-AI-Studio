import os
import sys


BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from config import Settings


class LLM_Model:
    def __init__(
        self,
        temperature,
        model_name="meta-llama/llama-4-scout-17b-16e-instruct",
        api_key=None,
    ) -> None:
        from langchain_groq import ChatGroq

        self.llm = ChatGroq(
            model=model_name,
            temperature=temperature,
            api_key=api_key or Settings.GROQ_API_KEY,
        )

    def get_model(self):
        return self.llm
