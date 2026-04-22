import os
from pathlib import Path

from dotenv import load_dotenv


# Load variables from backend/.env for local development and script execution.
load_dotenv(dotenv_path=Path(__file__).resolve().with_name(".env"))


class Settings:
    PEXELS_KEY = os.getenv("PEXELS_API_KEY")
    HF_TOKEN = os.getenv("HF_TOKEN")
    POLLINATIONS_KEY = os.getenv("POLLINATIONS_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
