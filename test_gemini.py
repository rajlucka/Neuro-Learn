import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

key = os.environ.get("GEMINI_API_KEY", "")

print(f"Key loaded: {'YES' if key else 'NO'}")
print(f"Key preview: {key[:8]}..." if key else "Key is empty")

try:
    genai.configure(api_key=key)
    model    = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content("Say hello in one sentence.")
    print(f"\nGemini response: {response.text}")
except Exception as e:
    print(f"\nError: {e}")