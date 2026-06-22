"""
AI meal planning helper using Google Gemini Flash (free tier).

Setup: add the variable GOOGLE_API_KEY to your Railway environment variables.
The google-generativeai library reads this variable automatically.
"""
import os
import json


def _recipe_context(recipes):
    lines = []
    for r in recipes:
        tags = ', '.join(t.name for t in r.recipe_tags.all()) or 'no tags'
        ings = ', '.join(i.name for i in r.ingredient_set.all())
        lines.append(
            f"RECIPE_ID:{r.id} | {r.title} | Tags: {tags} | "
            f"Time: {r.time} | Serves: {r.servings} | Ingredients: {ings}"
        )
    return '\n'.join(lines) if lines else 'No recipes available'


def _dinner_context(dinners):
    if not dinners:
        return 'No curated dinners available'
    lines = []
    for d in dinners:
        courses = ', '.join(
            f"{c.role}: {c.recipe.title}" for c in d.components.all()
        )
        lines.append(f"DINNER_ID:{d.id} | {d.title} | Courses: {courses}")
    return '\n'.join(lines)


def _pantry_context(pantry_items):
    if not pantry_items:
        return 'Pantry is empty'
    return '\n'.join(
        f"- {p.name} ({p.amount}), added {p.added_date.strftime('%Y-%m-%d')}"
        for p in pantry_items
    )


def suggest_meals(user_request, recipes, pantry_items, dinners=None, settings=None):
    """
    Returns (plan_data: dict, reasoning: str, error: str).

    plan_data keys:
      - items: list of {label, type ('recipe'|'dinner'), id, note}
      - suggested_imports: list of {label, search_query, reason}
      - reasoning: str
      - shopping_notes: str

    error is empty string on success.
    """
    env_var_name = 'GOOGLE_API_KEY'
    if not os.environ.get(env_var_name):
        return {}, '', (
            f'{env_var_name} is not set. '
            'Add it as a Railway environment variable and redeploy. '
            'Get a free key at aistudio.google.com/app/apikey'
        )

    try:
        from google import genai
    except ImportError:
        return {}, '', 'google-genai is not installed (check requirements.txt).'

    settings = settings or {}
    people = settings.get('people', '')
    days = settings.get('days', '')
    dietary = settings.get('dietary', [])
    max_time = settings.get('max_time', '')

    # Build a settings block to inject into the prompt
    settings_lines = []
    if people:
        settings_lines.append(f"- Number of people to cook for: {people}")
    if days:
        settings_lines.append(f"- Days to plan: {days}")
    if dietary:
        settings_lines.append(
            f"- Dietary restrictions (MUST be followed strictly): {', '.join(dietary)}"
        )
    if max_time:
        settings_lines.append(
            f"- Maximum cook time per meal: {max_time} minutes — "
            "exclude any recipe whose time exceeds this"
        )
    settings_block = (
        '\nUSER SETTINGS (follow these strictly):\n'
        + '\n'.join(settings_lines)
        + '\n'
    ) if settings_lines else ''

    try:
        client = genai.Client()  # reads GOOGLE_API_KEY from environment automatically

        recipe_ctx = _recipe_context(recipes)
        pantry_ctx = _pantry_context(pantry_items)
        dinner_ctx = _dinner_context(dinners or [])

        prompt = (
            "You are an expert weekly meal planner. Create a structured meal plan "
            "that best matches the user's request.\n\n"

            "RULES — follow every one of these:\n"
            "1. ONLY use RECIPE_IDs from 'Available recipes' or DINNER_IDs from "
            "'Curated dinners'. Never invent IDs.\n"
            "2. A 'dinner' entry is a full multi-course meal — do NOT add separate "
            "sides or extras alongside it.\n"
            "3. PRIORITIZE using pantry ingredients, especially the oldest items "
            "(listed first in the pantry).\n"
            "4. Aim for VARIETY — avoid the same main protein or cuisine two days "
            "in a row.\n"
            "5. Respect ALL dietary restrictions in SETTINGS — this is non-negotiable.\n"
            "6. Respect the max cook time — skip any recipe that clearly exceeds it.\n"
            "7. If the user requests something you cannot fill from the available "
            "lists, add it to 'suggested_imports' with a specific, searchable "
            "search_query (e.g. 'quick vegetarian lentil soup') so it can be "
            "imported later.\n"
            "8. Keep each 'note' to one short sentence explaining why the item "
            "was chosen.\n\n"

            + settings_block

            + "Return ONLY valid JSON with no markdown, no code fences, "
            "no extra text:\n"
            "{\n"
            '  "items": [\n'
            '    {"label": "Monday Dinner", "type": "recipe", "id": 42,'
            ' "note": "Uses pantry chicken and is quick"},\n'
            '    {"label": "Tuesday Dinner", "type": "dinner", "id": 3,'
            ' "note": "Full Italian spread, great for guests"},\n'
            '    {"label": "Wednesday Lunch", "type": "recipe", "id": 17,'
            ' "note": "Light and vegetarian"}\n'
            '  ],\n'
            '  "suggested_imports": [\n'
            '    {"label": "Friday Snack", "search_query": "healthy energy balls",'
            ' "reason": "No matching snack in the recipe library"}\n'
            '  ],\n'
            '  "reasoning": "One or two sentences summarising the overall plan",\n'
            '  "shopping_notes": "Key shopping tips — e.g. buy chicken fresh, '
            'check pantry for rice"\n'
            "}\n\n"

            f"User request:\n{user_request}\n\n"
            f"Available recipes:\n{recipe_ctx}\n\n"
            f"Curated dinners (full multi-course meals):\n{dinner_ctx}\n\n"
            f"Current pantry (oldest first — prioritise these):\n{pantry_ctx}"
        )

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        raw = response.text.strip()
        # Strip markdown code fences if the model adds them
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()

        data = json.loads(raw)
        return data, data.get('reasoning', ''), ''

    except json.JSONDecodeError:
        return {}, '', 'Could not parse AI response. Please try again.'
    except Exception as exc:
        return {}, '', f'AI request failed: {exc}'
