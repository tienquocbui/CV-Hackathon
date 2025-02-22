import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

try:
    response = openai.models.list()
    print("✅ API key works! Available models:", [model.id for model in response.data])
except Exception as e:
    print("❌ Error:", e)
