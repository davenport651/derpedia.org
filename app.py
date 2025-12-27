import os
import markdown
from flask import Flask, render_template, request
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURATION ---
# TODO: Enter your Gemini API Key here or set the GEMINI_API_KEY environment variable.
# You can obtain an API key from: https://aistudio.google.com/app/apikey
API_KEY = os.environ.get("GEMINI_API_KEY")
# ---------------------

if API_KEY:
    genai.configure(api_key=API_KEY)
    # Use a model that supports both text and images
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('q')
    image_file = request.files.get('image')

    if not API_KEY:
        # Graceful handling for missing API key
        content_md = "# API Key Missing\n\nPlease set the `GEMINI_API_KEY` environment variable or edit `app.py`. You can obtain one from Google AI Studio."
        content_html = markdown.markdown(content_md)
        return render_template('article.html', title="Configuration Error", content=content_html)

    try:
        if image_file and image_file.filename != '':
            # Image search
            image_data = {
                'mime_type': image_file.mimetype,
                'data': image_file.read()
            }
            prompt = "write a parody article in the style of wikipedia on the topic shown in the attached image"
            response = model.generate_content([prompt, image_data])
            title = "Image Search Result"
        else:
            # Text search
            full_prompt = f"you are writing for the parody newspaper The Onion and have been asked to write an article in the style of wikipedia on this topic: {query}"
            response = model.generate_content(full_prompt)
            title = query if query else "Parody Article"

        content_md = response.text
        # Naive title extraction if the model puts it in the first line
        if content_md.startswith("# "):
            lines = content_md.split('\n')
            candidate_title = lines[0].replace("# ", "").strip()
            # if the title seems reasonable (not too long), use it
            if len(candidate_title) < 100:
                title = candidate_title
                content_md = "\n".join(lines[1:])

        content_html = markdown.markdown(content_md)
        return render_template('article.html', title=title, content=content_html)

    except Exception as e:
        return render_template('article.html', title="Error", content=f"<p>An error occurred: {str(e)}</p>")

if __name__ == '__main__':
    app.run(debug=True, port=5000)
