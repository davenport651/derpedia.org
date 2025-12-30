import os
import google.genai

api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    client = google.genai.Client(api_key=api_key)
    try:
        models = client.models.list()
        for m in models:
            print(f"Name: {m.name}, Display: {m.display_name}")
    except Exception as e:
        print(f"Error listing models: {e}")
else:
    print("No API Key found")
