import os
import markdown
import io
import base64
import re
from flask import Flask, render_template, request, redirect, url_for, jsonify
from google import genai
from google.genai import types
from dotenv import load_dotenv
import database

# Load variables from .env file into os.environ
load_dotenv()

app = Flask(__name__)

# Initialize DB
database.init_db()

# --- CONFIGURATION ---
# TODO: Enter your Gemini API Key here or set the GEMINI_API_KEY environment variable.
# You can obtain an API key from: https://aistudio.google.com/app/apikey
API_KEY = os.environ.get("GEMINI_API_KEY")
#API_KEY = os.environ.get("")
# ---------------------

if API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    client = None
    print("Warning: GEMINI_API_KEY not found in .env file.")

def check_reality(query_text):
    """
    Asks the AI nicely if the user is making things up.
    Returns: True (It's real), False (It's fake/gibberish)
    """
    if not API_KEY:
        return True # Fail open if no key

    try:
        # Use the cheap/fast model for this check
        prompt = f"""
        You are a reality checker. content_check: '{query_text}'
        Does this concept/person/thing likely exist in the real world or pop culture?
        If it is total gibberish (like 'asdfjkl') or completely made up by a user smashing keys, reply NO.
        If it is a real thing, a misspelling of a real thing, or a fictional concept (like 'Unicorn'), reply YES.
        Reply ONLY with 'YES' or 'NO'.
        """
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        answer = response.text.strip().upper()

        return "YES" in answer
    except Exception as e:
        print(f"Reality check failed: {e}")
        # If the check fails (API error), assume it's real so we don't block users unnecessarily
        return True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/random')
def random_article():
    # Try to get from DB first
    article = database.get_random_article()
    if article:
        return redirect(url_for('search', q=article['query']))

    # Fallback to API generation if DB is empty
    if not API_KEY:
         return redirect(url_for('search', q="Configuration Error"))

    try:
        # Prompt for a random topic
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents="Generate a single, short, funny, parody Wikipedia topic phrase. Do not output anything else, just the phrase."
        )
        random_topic = response.text.strip()
        # Redirect to search with this topic
        return redirect(url_for('search', q=random_topic))
    except Exception as e:
        return redirect(url_for('search', q="Error generating random topic"))

@app.route('/report/<int:article_id>', methods=['POST'])
def report_article(article_id):
    database.mark_stale(article_id)
    return jsonify({"success": True})

@app.route('/recent')
def recent_articles():
    articles = database.get_recent_articles()
    return render_template('recent.html', articles=articles)

@app.route('/about')
def about():
    return render_template('about.html')

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

    if not query:
        query = "The Void"
    else:
        query = query.strip()

    # --- 1. Check Database (only for text queries) ---
    if not image_file:
        existing_article = database.get_article(query)
        if existing_article and not existing_article['is_stale']:
            return render_template_article(existing_article['title'], existing_article['content_md'], existing_article['image_b64'], existing_article['id'])

    if not API_KEY:
        content_md = "# API Key Missing\n\nPlease set the `GEMINI_API_KEY` environment variable or edit `app.py`."
        content_html = markdown.markdown(content_md)
        return render_template('article.html', title="Configuration Error", content=content_html)

    # --- 2. Reality Check (only for text queries) ---
    if not image_file:
        if not check_reality(query):
            return render_template('651.html', query=query), 651

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
            full_prompt = f"{structure_prompt} The topic is: {query}"
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=full_prompt
            )
            #title = query if query else "Parody Article"
            # Force Title Case for the default title (e.g. "dogzilla" -> "Dogzilla")
            title = query.title() if query else "Parody Article"
            image_prompt_text = f"A low resolution, photo for a Wikipedia parody article about {query}"

        content_md = ""
        generated_image_b64 = None

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
            try:
                # Attempt to use Imagen 4. Note: This requires the account to have access to the model.
                image_response = client.models.generate_images(
                    #model='gemini-2.0-flash-exp-image-generation', #alternative model; needs code development
                    model='imagen-4.0-fast-generate-001',
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
                print(f"Image generation failed: {img_err}. Note: 'imagen-4.0-fast-generate-001' might not be enabled for this API key.")
                # Non-blocking failure, just no image

            # Save to Database (only text queries)
            if not image_file:
                database.add_article(query, title, content_md, generated_image_b64)

            # Fetch back from DB to get ID or just render directly
            # To be efficient, we can just use the data we have.
            # But we need the ID for the report button.
            # If we just saved it, we can fetch it.
            if not image_file:
                 saved_article = database.get_article(query)
                 if saved_article:
                     return render_template_article(saved_article['title'], saved_article['content_md'], saved_article['image_b64'], saved_article['id'])

            # Fallback for image searches or DB failures
            return render_template_article(title, content_md, generated_image_b64, None)

        else:
             content_html = "<p>No content generated.</p>"
             return render_template('article.html', title=title, content=content_html)

    except Exception as e:
        return render_template('article.html', title="Error", content=f"<p>An error occurred: {str(e)}</p>")

def render_template_article(title, content_md, image_b64, article_id):
    # 3. Process Wiki-Links [[Topic]] -> <a href="/search?q=Topic">Topic</a>
    # We use a regex to replace [[...]] with links
    def replace_link(match):
        text = match.group(1)
        return f'<a href="{url_for("search", q=text)}">{text}</a>'

    content_md = re.sub(r'\[\[(.*?)\]\]', replace_link, content_md)

    # 4. Render Markdown
    content_html = markdown.markdown(content_md, extensions=['tables'])

    # 5. Inject Generated Image into the Infobox (if present) or at the top
    if image_b64:
        img_tag = f'<div class="infobox-image"><img src="data:image/png;base64,{image_b64}" alt="{title}"></div>'
        # Attempt to inject into the first table cell if it looks like an infobox
        # This is a bit hacky on HTML string, but standard markdown tables render as <table>...
        if "<table>" in content_html:
            # Injecting into the HTML string before the table:
            content_html = content_html.replace('<table>', f'<div class="infobox-container">{img_tag}<table>', 1).replace('</table>', '</table></div>', 1)
        else:
            # Fallback: float right image
            content_html = f'<div class="infobox-container">{img_tag}</div>' + content_html

    return render_template('article.html', title=title, content=content_html, article_id=article_id)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
