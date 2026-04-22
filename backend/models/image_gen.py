import requests
import random
import base64
from config import Settings

def generate_image_data(prompt: str, choice: int = 3) -> str:
    """
    Generates an image via Pollinations API and returns the Base64 encoded string.
    """
    try:
        # 1. Configuration: Map choice to dimensions
        if choice == 1:
            width, height = 1024, 1024  # Square
        elif choice == 2:
            width, height = 768, 1344   # Portrait
        else:
            width, height = 1280, 720   # Landscape (Default)

        seed = random.randint(1, 100000)
        encoded_prompt = requests.utils.quote(prompt)
        
        # 2. Construct URL
        url = f"https://gen.pollinations.ai/image/{encoded_prompt}"
        
        params = {
            "model": "flux",
            "width": width,
            "height": height,
            "seed": seed,
            "nologo": "true"
        }

        # 3. Authenticated Request
        # We use the Secret Key here in the headers
        headers = {
            "Authorization": f"Bearer {Settings.POLLINATIONS_KEY}"
        }

        print(f"🎨 Generating: {prompt} ({width}x{height})...")
        
        response = requests.get(url, params=params, headers=headers)

        # 4. Return Base64 String
        if response.status_code == 200:
            # Convert raw bytes -> Base64 string
            img_b64 = base64.b64encode(response.content).decode("utf-8")
            return img_b64
        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"❌ System Error: {e}")
        return None