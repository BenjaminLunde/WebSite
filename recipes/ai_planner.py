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
        lines.append(f"ID:{r.id} - {r.title} [Tags: {tags}] [Ingredients: {ings}]")
    return '\n'.join(lines)


def _pantry_context(pantry_items):
    if not pantry_items:
        return 'Pantry is empty'
    return '\n'.join(
        f"{p.name} ({p.amount}) - added {p.added_date.strftime('%Y-%m-%d')}"
        for p in pantry_items
    )


def suggest_meals(user_request, recipes, pantry_items):
    """
    Returns (suggestion_ids: list[int], reasoning: str, error: str).
    error is empty string on success.
    """
    env_var_name = 'GOOGLE_API_KEY'
    if not os.environ.get(env_var_name):
        return [], '', (
            f'{env_var_name} is not set. '
            'Add it as a Railway environment variable and redeploy. '
            'Get a free token at aistudio.google.com/app/apikey'
        )

    try:
        import google.generativeai as genai
    except ImportError:
        return [], '', 'google-generativeai is not installed (check requirements.txt).'

    try:
        # genai reads GOOGLE_API_KEY from the environment automatically
        gmodel = genai.GenerativeModel('gemini-2.5-flash')

        recipe_ctx = _recipe_context(recipes)
        pantry_ctx = _pantry_context(pantry_items)

        prompt = (
            "You are a helpful meal planner. Suggest recipes from the list below "
            "that best match the user's request.\n"
            "Prioritize recipes whose ingredients are in the pantry, "
            "especially older items (listed first).\n"
            "Return ONLY valid JSON, no markdown, no extra text:\n"
            '{"suggestions": [id, ...], "reasoning": "short explanation"}\n\n'
            f"User request: {user_request}\n\n"
            f"Available recipes:\n{recipe_ctx}\n\n"
            f"Pantry (oldest first):\n{pantry_ctx}"
        )

        response = gmodel.generate_content(prompt)
        raw = response.text.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()

        data = json.loads(raw)
        ids = [int(i) for i in data.get('suggestions', [])]
        reason = data.get('reasoning', '')
        return ids, reason, ''

    except json.JSONDecodeError:
        return [], '', 'Could not parse AI response. Please try again.'
    except Exception as exc:
        return [], '', f'AI request failed: {exc}'
