import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("VISION_API_KEY", "YOUR_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"

resp = requests.get(url)
print(resp.json())
