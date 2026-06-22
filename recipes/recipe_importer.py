"""
Recipe importer — fetch a cooking website and parse it with Gemini AI.

Workflow:
  1. User picks a trusted source (RecipeSource) or pastes a URL directly.
  2. We fetch the page and strip it to readable text.
  3. Gemini extracts the recipe as structured JSON.
  4. We create a draft Info + Ingredients + Instructions in the database.

Requires GOOGLE_API_KEY environment variable (same one used by the meal planner).
"""
import os
import json
import urllib.parse

try:
    import requests
    from bs4 import BeautifulSoup
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False


# ---------------------------------------------------------------------------
# Page fetching
# ---------------------------------------------------------------------------

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'en-US,en;q=0.9',
}


def fetch_page_text(url, max_chars=25000):
    """
    Fetch *url* and return clean readable text (HTML tags stripped).
    Raises RuntimeError if the page cannot be fetched.
    """
    if not _HAS_REQUESTS:
        raise RuntimeError(
            "The 'requests' and 'beautifulsoup4' packages are required. "
            "Add them to requirements.txt and redeploy."
        )
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=12)
        resp.raise_for_status()
    except Exception as exc:
        raise RuntimeError(f"Could not fetch '{url}': {exc}") from exc

    soup = BeautifulSoup(resp.text, 'html.parser')
    # Remove noise tags
    for tag in soup(['script', 'style', 'noscript', 'nav', 'footer', 'header', 'aside']):
        tag.decompose()
    text = soup.get_text(separator='\n', strip=True)
    return text[:max_chars]


def get_links_from_page(url, base_url):
    """
    Fetch *url* and return all href links that start with *base_url*.
    Used to extract recipe links from a search-results page.
    """
    if not _HAS_REQUESTS:
        return []
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=12)
        resp.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Handle relative URLs
        if href.startswith('/'):
            href = base_url.rstrip('/') + href
        if href.startswith(base_url) and href != base_url:
            links.append(href)
    return links


# ---------------------------------------------------------------------------
# Gemini parsing
# ---------------------------------------------------------------------------

_PARSE_PROMPT = """\
Extract the recipe from the text below and return ONLY valid JSON \
(no markdown, no extra text) in exactly this format:

{
  "title": "Recipe name",
  "intro": "One or two sentence description",
  "servings": 4,
  "time": "30 min",
  "difficulty": 3,
  "ingredients": [
    {"name": "flour", "amount": "200 g"},
    {"name": "eggs", "amount": "2 stk"}
  ],
  "instructions": [
    "First step.",
    "Second step."
  ]
}

Rules:
- difficulty is 1 (very easy) to 5 (very hard).
- Use metric measurements (g, kg, dl, l, ts=teaspoon, ss=tablespoon) where possible.
- "stk" means pieces/items (e.g. "2 stk" for 2 eggs).
- Keep the instructions clear and concise — one action per step.
- If a field is unknown, use a sensible default (servings=4, difficulty=2, time="unknown").

Text:
"""


def gemini_parse_recipe(page_text):
    """
    Ask Gemini to extract a structured recipe from *page_text*.
    Returns (data_dict, error_string). On success error_string is ''.
    """
    env_var = 'GOOGLE_API_KEY'
    if not os.environ.get(env_var):
        return None, (
            f'{env_var} is not set. '
            'Add it as a Railway environment variable.'
        )

    try:
        import google.generativeai as genai
    except ImportError:
        return None, 'google-generativeai is not installed (check requirements.txt).'

    try:
        gmodel = genai.GenerativeModel('gemini-2.5-flash')
        response = gmodel.generate_content(_PARSE_PROMPT + page_text)
        raw = response.text.strip()
        # Strip markdown code fences if present
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
        data = json.loads(raw)
        return data, ''
    except json.JSONDecodeError:
        return None, 'Gemini returned a response that could not be parsed as JSON. Try again.'
    except Exception as exc:
        return None, f'AI request failed: {exc}'


# ---------------------------------------------------------------------------
# High-level import helpers
# ---------------------------------------------------------------------------

_GENERATE_PROMPT = """\
Write a complete, authentic recipe for the dish described below, \
then return ONLY valid JSON (no markdown, no extra text) in exactly this format:

{
  "title": "Recipe name",
  "intro": "One or two sentence description",
  "servings": 4,
  "time": "30 min",
  "difficulty": 3,
  "ingredients": [
    {"name": "flour", "amount": "200 g"},
    {"name": "eggs", "amount": "2 stk"}
  ],
  "instructions": [
    "First step.",
    "Second step."
  ]
}

Rules:
- difficulty is 1 (very easy) to 5 (very hard).
- Use metric measurements (g, kg, dl, l, ts=teaspoon, ss=tablespoon) where possible.
- "stk" means pieces/items (e.g. "2 stk" for 2 eggs).
- Keep instructions clear and concise — one action per step.
- Make the recipe practical and realistic for a home cook.

Dish:
"""


def generate_recipe(query):
    """
    Ask Gemini to invent a recipe for *query* from its own knowledge.
    No web scraping — Gemini writes the recipe itself.
    Returns (data_dict, error_string).
    """
    env_var = 'GOOGLE_API_KEY'
    if not os.environ.get(env_var):
        return None, (
            f'{env_var} is not set. '
            'Add it as a Railway environment variable.'
        )

    try:
        import google.generativeai as genai
    except ImportError:
        return None, 'google-generativeai is not installed (check requirements.txt).'

    try:
        gmodel = genai.GenerativeModel('gemini-2.5-flash')
        response = gmodel.generate_content(_GENERATE_PROMPT + query)
        raw = response.text.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
        data = json.loads(raw)
        return data, ''
    except json.JSONDecodeError:
        return None, 'Gemini returned a response that could not be parsed as JSON. Try again.'
    except Exception as exc:
        return None, f'AI request failed: {exc}'


def import_from_url(url):
    """
    Fetch *url*, parse the recipe with Gemini.
    Returns (data_dict, source_url, error_string).
    """
    try:
        text = fetch_page_text(url)
    except RuntimeError as exc:
        return None, url, str(exc)

    data, error = gemini_parse_recipe(text)
    return data, url, error


def search_and_import(query, sources):
    """
    Try each active RecipeSource to find and import a recipe matching *query*.
    Fetches the source's search page, picks the first recipe link,
    then calls import_from_url on it.

    Returns (data_dict, source_url, error_string).
    """
    errors = []
    for source in sources:
        if not source.search_url_pattern:
            continue

        search_url = source.search_url_pattern.replace(
            '{query}', urllib.parse.quote_plus(query)
        )
        links = get_links_from_page(search_url, source.base_url)

        # Filter to plausible recipe URLs (longer paths, not just the base)
        recipe_links = [
            l for l in links
            if len(l) > len(source.base_url) + 10
            and not any(x in l for x in ['search', 'category', 'tag', 'page', 'login', 'signup'])
        ]

        if not recipe_links:
            errors.append(f"{source.name}: no recipe links found in search results.")
            continue

        data, url, error = import_from_url(recipe_links[0])
        if data:
            return data, url, ''
        errors.append(f"{source.name}: {error}")

    summary = ' | '.join(errors) if errors else 'No sources with search patterns configured.'
    return None, '', f'Could not find a recipe: {summary}'


# ---------------------------------------------------------------------------
# Database creation
# ---------------------------------------------------------------------------

def create_draft_recipe(data):
    """
    Create a draft Info record (+ Ingredients + Instructions) from *data*.
    *data* is the dict returned by gemini_parse_recipe / import_from_url.
    Returns the saved Info instance.
    """
    from django.utils import timezone
    from .models import Info, Ingredient, IngredientType, Instruction

    recipe = Info(
        title=data.get('title', 'Imported Recipe'),
        intro=data.get('intro', ''),
        servings=int(data.get('servings', 4)),
        time=str(data.get('time', 'unknown')),
        difficulty=int(data.get('difficulty', 2)),
        pub_date=timezone.now(),
        is_draft=True,
    )
    recipe.save()

    # Ingredients
    for ing in data.get('ingredients', []):
        name = ing.get('name', '').strip()
        amount = ing.get('amount', '').strip()
        if not name:
            continue
        itype, _ = IngredientType.objects.get_or_create(name=name)
        Ingredient.objects.create(
            info=recipe,
            ingredient_type=itype,
            measurment=amount,
        )

    # Instructions
    for step_text in data.get('instructions', []):
        text = str(step_text).strip()
        if text:
            Instruction.objects.create(info=recipe, text=text)

    return recipe
