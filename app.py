import os
import markdown
import io
import base64
import re
from flask import Flask, render_template, request, redirect, url_for
from google import genai
from google.genai import types

app = Flask(__name__)

# --- CONFIGURATION ---
# TODO: Enter your Gemini API Key here or set the GEMINI_API_KEY environment variable.
# You can obtain an API key from: https://aistudio.google.com/app/apikey
API_KEY = os.environ.get("GEMINI_API_KEY")
# ---------------------

if API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    client = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/random')
def random_article():
    if not API_KEY:
         return redirect(url_for('search', q="Configuration Error"))

    try:
        # Prompt for a random topic
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents="Generate a single, short, funny, parody Wikipedia topic phrase. Do not output anything else, just the phrase."
        )
        random_topic = response.text.strip()
        # Redirect to search with this topic
        return redirect(url_for('search', q=random_topic))
    except Exception as e:
        return redirect(url_for('search', q="Error generating random topic"))


@app.route('/search', methods=['POST', 'GET'])
def search():
    if request.method == 'POST':
        query = request.form.get('q')
        image_file = request.files.get('image')
        # Check for "I'm Feeling Derpy" button press if it was a named submit button
        if 'derpy' in request.form:
             return redirect(url_for('random_article'))
    else:
        # GET request (from wiki-links or direct URL)
        query = request.args.get('q')
        image_file = None

    if not API_KEY:
        content_md = "# API Key Missing\n\nPlease set the `GEMINI_API_KEY` environment variable or edit `app.py`."
        content_html = markdown.markdown(content_md)
        return render_template('article.html', title="Configuration Error", content=content_html)

    try:
        response_text = ""
        title = "Parody Article"

        # Base instructions for structure
        structure_prompt = (
            "You are an absurdist, confidently incorrect contributor to 'Derpedia,' a satirical encyclopedia dedicated to hilarious misinformation. "
            "Write a short encyclopedia entry. "
            "Structure Requirements: "
            "1. The very first line must be the title of the article, starting with '# ' (e.g., '# Title'). "
            "2. Immediately follow the title with a Markdown table representing a Wikipedia infobox (key-value pairs). "
            "3. Summary. "
            "4. Origin/History. "
            "5. Controversy. "
            "6. Use '[[Topic]]' syntax for pseudo-links to other funny topics."
        )

        if image_file and image_file.filename != '':
            # Image search
            image_bytes = image_file.read()
            prompt = f"{structure_prompt} Write the article based on the attached image."

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    prompt,
                    types.Part.from_bytes(data=image_bytes, mime_type=image_file.mimetype)
                ]
            )
            title = "Image Search Result"
            image_prompt_text = "A funny parody image based on this uploaded image" # Fallback for generation
        else:
            # Text search
            # Fallback if query is missing to avoid "None" articles
            if not query:
                query = "The Void"

            full_prompt = f"{structure_prompt} The topic is: {query}"
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=full_prompt
            )
            title = query if query else "Parody Article"
            image_prompt_text = f"A low resolution, funny parody image for a Wikipedia article about {query}"

        content_md = ""
        if response.text:
            content_md = response.text

            # 1. Extract Title
            if content_md.startswith("# "):
                lines = content_md.split('\n')
                candidate_title = lines[0].replace("# ", "").strip()
                if len(candidate_title) < 100:
                    title = candidate_title
                    content_md = "\n".join(lines[1:])

            # 2. Generate Image (Imagen)
            generated_image_b64 = None
            try:
                # Attempt to use Imagen 3. Note: This requires the account to have access to the model.
                image_response = client.models.generate_images(
                    model='imagen-3.0-generate-001',
                    prompt=image_prompt_text,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                    )
                )
                if image_response.generated_images:
                    img_bytes = image_response.generated_images[0].image.image_bytes
                    generated_image_b64 = base64.b64encode(img_bytes).decode('utf-8')
            except Exception as img_err:
                # detailed logging for the user to debug
                print(f"Image generation failed: {img_err}. Note: 'imagen-3.0-generate-001' might not be enabled for this API key.")
                # Non-blocking failure, just no image

            # 3. Process Wiki-Links [[Topic]] -> <a href="/search?q=Topic">Topic</a>
            # We use a regex to replace [[...]] with links
            def replace_link(match):
                text = match.group(1)
                return f'<a href="{url_for("search", q=text)}">{text}</a>'

            content_md = re.sub(r'\[\[(.*?)\]\]', replace_link, content_md)

            # 4. Render Markdown
            content_html = markdown.markdown(content_md, extensions=['tables'])

            # 5. Inject Generated Image into the Infobox (if present) or at the top
            if generated_image_b64:
                img_tag = f'<div class="infobox-image"><img src="data:image/png;base64,{generated_image_b64}" alt="{title}"></div>'
                # Attempt to inject into the first table cell if it looks like an infobox
                # This is a bit hacky on HTML string, but standard markdown tables render as <table>...
                if "<table>" in content_html:
                    # Insert before the table closes or at start?
                    # Actually, standard Wikipedia infoboxes have images at the top.
                    # Let's try to prepend it to the table if we can find it.
                    # Or simpler: Just wrap the table in a div and put the image there?
                    # Let's rely on CSS. We will pass the image separately or inject it.
                    # Injecting into the HTML string before the table:
                    content_html = content_html.replace('<table>', f'<div class="infobox-container">{img_tag}<table>', 1).replace('</table>', '</table></div>', 1)
                else:
                    # Fallback: float right image
                    content_html = f'<div class="infobox-container">{img_tag}</div>' + content_html

        else:
             content_html = "<p>No content generated.</p>"
             generated_image_b64 = None

        return render_template('article.html', title=title, content=content_html)

    except Exception as e:
        return render_template('article.html', title="Error", content=f"<p>An error occurred: {str(e)}</p>")

if __name__ == '__main__':
    app.run(debug=True, port=5000)
