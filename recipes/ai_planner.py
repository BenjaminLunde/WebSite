"""
AI meal planning helper using Claude (Anthropic).

Setup: add the variable ANTHROPIC_API_KEY to your Railway environment variables.
The anthropic library reads this variable automatically.
"""
import os
import json
from datetime import date


def _recipe_context(recipes):
    lines = []
    for r in recipes:
        tags = ', '.join(t.name for t in r.recipe_tags.all()) or 'no tags'
        ings = ', '.join(i.name for i in r.ingredient_set.all())
        score = f"{r.score}/10" if r.score is not None else 'unrated'
        last_cooked = r.last_cooked.strftime('%Y-%m-%d') if r.last_cooked else 'never'
        lines.append(
            f"RECIPE_ID:{r.id} | {r.title} | Score: {score} | Last cooked: {last_cooked} | "
            f"Tags: {tags} | Time: {r.time} | Serves: {r.servings} | Ingredients: {ings}"
        )
    return '\n'.join(lines) if lines else 'No recipes available'


def _dinner_context(dinners):
    """
    Format curated dinners for the AI prompt.

    Dinners are flexible templates, not fixed menus. Each role (Main, Side, Sauce…)
    can have multiple recipe options — default_selected marks the classic/traditional
    choice, while non-default ones are alternatives the user can swap in.
    We surface this structure so the AI understands that dinners have variations.
    """
    if not dinners:
        return 'No curated dinners available'
    lines = []
    for d in dinners:
        # Group components by role, preserving order
        role_groups = {}
        role_order = []
        for c in d.components.all():
            if c.role not in role_groups:
                role_groups[c.role] = []
                role_order.append(c.role)
            role_groups[c.role].append(c)

        role_parts = []
        for role in role_order:
            comps = role_groups[role]
            if len(comps) == 1:
                # Single option — straightforward
                role_parts.append(f"{role}: {comps[0].recipe.title}")
            else:
                # Multiple options — show classic defaults, then alternatives
                defaults = [c.recipe.title for c in comps if c.default_selected]
                alts = [c.recipe.title for c in comps if not c.default_selected]
                classic = ', '.join(defaults) if defaults else comps[0].recipe.title
                part = f"{role}: {classic}"
                if alts:
                    part += f" (alternatives: {', '.join(alts)})"
                role_parts.append(part)

        lines.append(f"DINNER_ID:{d.id} | {d.title} | {' | '.join(role_parts)}")
    return '\n'.join(lines)


def _pantry_context(pantry_items):
    if not pantry_items:
        return 'Pantry is empty'

    # Exclude "always available" items (water etc.) — they're never in the pantry
    relevant = [p for p in pantry_items if not (p.ingredient_type and p.ingredient_type.is_always_available)]
    staples = [p for p in relevant if p.ingredient_type and p.ingredient_type.is_staple]
    perishables = [p for p in relevant if not (p.ingredient_type and p.ingredient_type.is_staple)]

    lines = []
    if perishables:
        lines.append('Perishables — prioritise the oldest (listed first):')
        for p in sorted(perishables, key=lambda x: x.added_date):
            lines.append(f"  - {p.name} ({p.amount}), added {p.added_date.strftime('%Y-%m-%d')}")
    if staples:
        lines.append('Pantry staples (always available — no need to rush these):')
        for p in staples:
            lines.append(f"  - {p.name} ({p.amount})")

    return '\n'.join(lines) if lines else 'Pantry is empty'


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
    env_var_name = 'ANTHROPIC_API_KEY'
    if not os.environ.get(env_var_name):
        return {}, '', (
            f'{env_var_name} is not set. '
            'Add it as a Railway environment variable and redeploy. '
            'Get a key at console.anthropic.com'
        )

    try:
        import anthropic
    except ImportError:
        return {}, '', 'anthropic is not installed (check requirements.txt).'

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
        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment automatically

        recipe_ctx = _recipe_context(recipes)
        pantry_ctx = _pantry_context(pantry_items)
        dinner_ctx = _dinner_context(dinners or [])
        today = date.today().strftime('%Y-%m-%d')

        prompt = (
            f"You are an expert weekly meal planner. Today's date is {today}. "
            "Create a structured meal plan that best matches the user's request.\n\n"

            "RULES — follow every one of these:\n"
            "1. ONLY use RECIPE_IDs from 'Available recipes' or DINNER_IDs from "
            "'Curated dinners'. Never invent IDs.\n"
            "2. Complete meals come in two forms — treat both as standalone dinners that need no extra sides:\n"
            "   a) A 'dinner' entry (type=dinner) is a curated multi-course template. Each role lists a "
            "classic default and possibly alternative options. The user picks their exact combination on "
            "the dinner page. Mention the classic combination in your note.\n"
            "   b) A recipe tagged 'Dinner' is a complete standalone meal in its own right — "
            "it does not need sides or extras suggested alongside it.\n"
            "   Do NOT add separate individual recipes alongside either type.\n"
            "3. PRIORITIZE using perishable pantry ingredients (oldest first). "
            "Pantry staples (flour, sugar, spices, etc.) are always available — "
            "don't prioritise them just because they've been there a long time.\n"
            "4. INGREDIENT OVERLAP — prefer combinations of recipes that share "
            "ingredients where possible to reduce shopping waste. "
            "Note: ingredient lists are indicative, not exact — proteins and vegetables "
            "are often interchangeable in a recipe. Think in broader families "
            "(e.g. root vegetables, leafy greens, white fish) rather than exact ingredient matches.\n"
            "5. Respect ALL dietary restrictions in SETTINGS — this is non-negotiable.\n"
            "6. Respect the max cook time — skip any recipe that clearly exceeds it.\n"
            "7. If the user requests something you cannot fill from the available "
            "lists, add it to 'suggested_imports' with a specific, searchable "
            "search_query (e.g. 'quick vegetarian lentil soup') so it can be "
            "imported later.\n"
            "8. Keep each 'note' to one short sentence explaining why the item "
            "was chosen.\n"
            "9. SCORE & RECENCY — use these fields on each recipe to rank candidates:\n"
            "   - Prefer higher-scored recipes (8–10 are proven favourites; 6–7 are solid).\n"
            "   - 'unrated' means the recipe has never been scored — good to include so it can be evaluated.\n"
            "   - Avoid recipes cooked in the last 14 days — too recent to repeat.\n"
            "   - Target roughly a 4-week frequency: anything last cooked 4+ weeks ago is fair game.\n"
            "   - 'last cooked: never' means the recipe has never been made — treat as a great candidate to try.\n"
            "   - A recipe can still be included if last cooked 4+ weeks ago even if its score is not the highest, "
            "especially if the user's pantry or request steers towards it.\n\n"

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
            f"Current pantry:\n{pantry_ctx}"
        )

        response = client.messages.create(
            model='claude-haiku-4-5',
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown code fences if the model adds them
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()

        data = json.loads(raw)
        return data, data.get('reasoning', ''), ''

    except json.JSONDecodeError:
        return {}, '', 'Could not parse AI response. Please try again.'
    except Exception as exc:
        return {}, '', f'AI request failed: {exc}'
