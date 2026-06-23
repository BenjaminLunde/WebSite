import os
import json
from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from recipes.models import (
    Ingredient, Instruction, Tagg, RecipeTag, PantryItem,
    IngredientType, Dinner, DinnerComponent, RecipeSource,
    IngredientToShop,
)
from django.contrib.auth.models import User

from .models import Info


# ---------------------------------------------------------------------------
# Seed data — common Norwegian ingredient types
# (name, tagg_name, shelf_life_days, is_staple, is_always_available)
# ---------------------------------------------------------------------------
_SEED_DATA = [
    # ── Frukt og Grønt ──────────────────────────────────────────────────────
    ('Eple',              'Frukt og Grønt', 14,   False, False),
    ('Pære',              'Frukt og Grønt', 10,   False, False),
    ('Banan',             'Frukt og Grønt',  7,   False, False),
    ('Appelsin',          'Frukt og Grønt', 14,   False, False),
    ('Sitron',            'Frukt og Grønt', 21,   False, False),
    ('Lime',              'Frukt og Grønt', 14,   False, False),
    ('Mango',             'Frukt og Grønt',  5,   False, False),
    ('Ananas',            'Frukt og Grønt',  5,   False, False),
    ('Jordbær',           'Frukt og Grønt',  4,   False, False),
    ('Bringebær',         'Frukt og Grønt',  4,   False, False),
    ('Blåbær',            'Frukt og Grønt',  7,   False, False),
    ('Druer',             'Frukt og Grønt',  7,   False, False),
    ('Avokado',           'Frukt og Grønt',  4,   False, False),
    ('Nektarin',          'Frukt og Grønt',  5,   False, False),
    ('Fersken',           'Frukt og Grønt',  5,   False, False),
    ('Selleri',           'Frukt og Grønt', 14,   False, False),
    ('Purre',             'Frukt og Grønt', 10,   False, False),
    ('Spinat',            'Frukt og Grønt',  5,   False, False),
    ('Isbergsalat',       'Frukt og Grønt',  7,   False, False),
    ('Rucola',            'Frukt og Grønt',  5,   False, False),
    ('Sjalottløk',        'Frukt og Grønt', 30,   False, False),
    ('Sjampinjong',       'Frukt og Grønt',  7,   False, False),
    ('Sopp',              'Frukt og Grønt',  5,   False, False),
    ('Aubergine',         'Frukt og Grønt', 10,   False, False),
    ('Zucchini',          'Frukt og Grønt',  7,   False, False),
    ('Squash',            'Frukt og Grønt',  7,   False, False),
    ('Rosenkål',          'Frukt og Grønt', 10,   False, False),
    ('Kålrabi',           'Frukt og Grønt', 14,   False, False),
    ('Pastinakk',         'Frukt og Grønt', 14,   False, False),
    ('Cherrytomater',     'Frukt og Grønt',  7,   False, False),
    ('Mais',              'Frukt og Grønt',  3,   False, False),
    ('Persille',          'Frukt og Grønt',  7,   False, False),
    ('Basilikum',         'Frukt og Grønt',  7,   False, False),
    ('Dill',              'Frukt og Grønt',  7,   False, False),
    ('Timian',            'Frukt og Grønt',  7,   False, False),
    ('Rosmarin',          'Frukt og Grønt', 10,   False, False),

    # ── Kjøtt og Fisk ───────────────────────────────────────────────────────
    ('Kyllingfilet',      'Kjøtt og Fisk',   3,   False, False),
    ('Kyllingbryst',      'Kjøtt og Fisk',   3,   False, False),
    ('Kyllinglår',        'Kjøtt og Fisk',   3,   False, False),
    ('Kjøttdeig',         'Kjøtt og Fisk',   3,   False, False),
    ('Lammekjøtt',        'Kjøtt og Fisk',   3,   False, False),
    ('Svinekoteletter',   'Kjøtt og Fisk',   3,   False, False),
    ('Svinefilet',        'Kjøtt og Fisk',   3,   False, False),
    ('Bacon',             'Kjøtt og Fisk',   7,   False, False),
    ('Pølser',            'Kjøtt og Fisk',   5,   False, False),
    ('Kokt skinke',       'Kjøtt og Fisk',   5,   False, False),
    ('Spekeskinke',       'Kjøtt og Fisk',  14,   False, False),
    ('Laks',              'Kjøtt og Fisk',   2,   False, False),
    ('Laksefilet',        'Kjøtt og Fisk',   2,   False, False),
    ('Torsk',             'Kjøtt og Fisk',   2,   False, False),
    ('Sei',               'Kjøtt og Fisk',   2,   False, False),
    ('Reker',             'Kjøtt og Fisk',   2,   False, False),
    ('Blåskjell',         'Kjøtt og Fisk',   1,   False, False),
    ('Tunfisk',           'Kjøtt og Fisk',  None, True,  False),
    ('Makrell',           'Kjøtt og Fisk',  None, True,  False),

    # ── Egg og Meieriprodukter ──────────────────────────────────────────────
    ('Egg',               'Egg og Meieriprodukter', 21,   False, False),
    ('Rømme',             'Egg og Meieriprodukter', 14,   False, False),
    ('Kremfløte',         'Egg og Meieriprodukter', 10,   False, False),
    ('Matfløte',          'Egg og Meieriprodukter', 10,   False, False),
    ('Yoghurt',           'Egg og Meieriprodukter', 14,   False, False),
    ('Gresk yoghurt',     'Egg og Meieriprodukter', 14,   False, False),
    ('Cheddar',           'Egg og Meieriprodukter', 30,   False, False),
    ('Mozzarella',        'Egg og Meieriprodukter', 14,   False, False),
    ('Parmesan',          'Egg og Meieriprodukter', 45,   False, False),
    ('Crème fraîche',     'Egg og Meieriprodukter', 14,   False, False),
    ('Cottage cheese',    'Egg og Meieriprodukter',  7,   False, False),
    ('Hvitost',           'Egg og Meieriprodukter', 30,   False, False),
    ('Brunost',           'Egg og Meieriprodukter', 60,   False, False),
    ('Fetaost',           'Egg og Meieriprodukter', 30,   False, False),
    ('Mascarpone',        'Egg og Meieriprodukter', 14,   False, False),
    ('Kesam',             'Egg og Meieriprodukter', 10,   False, False),
    ('Brie',              'Egg og Meieriprodukter', 14,   False, False),

    # ── Hermetikk og Tørrvarrer ─────────────────────────────────────────────
    ('Ris',               'Hermetikk og Tørrvarrer', None, True,  False),
    ('Basmatiris',        'Hermetikk og Tørrvarrer', None, True,  False),
    ('Jasminris',         'Hermetikk og Tørrvarrer', None, True,  False),
    ('Risottoris',        'Hermetikk og Tørrvarrer', None, True,  False),
    ('Penne',             'Hermetikk og Tørrvarrer', None, True,  False),
    ('Fusilli',           'Hermetikk og Tørrvarrer', None, True,  False),
    ('Lasagneplater',     'Hermetikk og Tørrvarrer', None, True,  False),
    ('Makaroni',          'Hermetikk og Tørrvarrer', None, True,  False),
    ('Tagliatelle',       'Hermetikk og Tørrvarrer', None, True,  False),
    ('Linser',            'Hermetikk og Tørrvarrer', None, True,  False),
    ('Røde linser',       'Hermetikk og Tørrvarrer', None, True,  False),
    ('Svarte bønner',     'Hermetikk og Tørrvarrer', None, True,  False),
    ('Kidneybønner',      'Hermetikk og Tørrvarrer', None, True,  False),
    ('Hermetiske tomater','Hermetikk og Tørrvarrer', None, True,  False),
    ('Tomatpuré',         'Hermetikk og Tørrvarrer', None, True,  False),
    ('Hermetisk mais',    'Hermetikk og Tørrvarrer', None, True,  False),
    ('Ketchup',           'Hermetikk og Tørrvarrer', None, True,  False),
    ('Majones',           'Hermetikk og Tørrvarrer', None, True,  False),
    ('Sennep',            'Hermetikk og Tørrvarrer', None, True,  False),
    ('Dijon-sennep',      'Hermetikk og Tørrvarrer', None, True,  False),
    ('Olivenolje',        'Hermetikk og Tørrvarrer', None, True,  False),
    ('Solsikkeolje',      'Hermetikk og Tørrvarrer', None, True,  False),
    ('Rapsolje',          'Hermetikk og Tørrvarrer', None, True,  False),
    ('Hvetemel',          'Hermetikk og Tørrvarrer', None, True,  False),
    ('Havregryn',         'Hermetikk og Tørrvarrer', None, True,  False),
    ('Melis',             'Hermetikk og Tørrvarrer', None, True,  False),
    ('Bakepulver',        'Hermetikk og Tørrvarrer', None, True,  False),
    ('Natron',            'Hermetikk og Tørrvarrer', None, True,  False),
    ('Tørrgjær',          'Hermetikk og Tørrvarrer', None, True,  False),
    ('Vaniljesukker',     'Hermetikk og Tørrvarrer', None, True,  False),
    ('Kakao',             'Hermetikk og Tørrvarrer', None, True,  False),
    ('Flakesalt',         'Hermetikk og Tørrvarrer', None, True,  False),
    ('Mandler',           'Hermetikk og Tørrvarrer', None, True,  False),
    ('Valnøtter',         'Hermetikk og Tørrvarrer', None, True,  False),
    ('Cashewnøtter',      'Hermetikk og Tørrvarrer', None, True,  False),
    ('Rosiner',           'Hermetikk og Tørrvarrer', None, True,  False),
    ('Peanøttsmør',       'Hermetikk og Tørrvarrer', None, True,  False),
    ('Tahini',            'Hermetikk og Tørrvarrer', None, True,  False),
    ('Kokoskrem',         'Hermetikk og Tørrvarrer', None, True,  False),
    ('Buljongterning',    'Hermetikk og Tørrvarrer', None, True,  False),
    ('Grønnsakskraft',    'Hermetikk og Tørrvarrer', None, True,  False),
    ('Worcestershiresaus','Hermetikk og Tørrvarrer', None, True,  False),
    ('Fiskesaus',         'Hermetikk og Tørrvarrer', None, True,  False),
    ('Sriracha',          'Hermetikk og Tørrvarrer', None, True,  False),
    ('Balsamicoeddik',    'Hermetikk og Tørrvarrer', None, True,  False),
    ('Rødvinseddik',      'Hermetikk og Tørrvarrer', None, True,  False),
    ('Knekkebrød',        'Hermetikk og Tørrvarrer', None, True,  False),
    ('Tortillalefser',    'Hermetikk og Tørrvarrer',  7,   False, False),
    ('Loff',              'Hermetikk og Tørrvarrer',  3,   False, False),
    ('Soyamelk',          'Hermetikk og Tørrvarrer',  7,   False, False),

    # ── Krydder (all staples, no shelf life) ────────────────────────────────
    ('Kanel',             'Krydder', None, True, False),
    ('Gurkemeie',         'Krydder', None, True, False),
    ('Paprikapulver',     'Krydder', None, True, False),
    ('Røkt paprikapulver','Krydder', None, True, False),
    ('Cayennepepper',     'Krydder', None, True, False),
    ('Hvit pepper',       'Krydder', None, True, False),
    ('Chiliflak',         'Krydder', None, True, False),
    ('Løkpulver',         'Krydder', None, True, False),
    ('Hvitløkspulver',    'Krydder', None, True, False),
    ('Ingefærpulver',     'Krydder', None, True, False),
    ('Tørket timian',     'Krydder', None, True, False),
    ('Tørket rosmarin',   'Krydder', None, True, False),
    ('Tørket basilikum',  'Krydder', None, True, False),
    ('Tørket dill',       'Krydder', None, True, False),
    ('Laurbærblad',       'Krydder', None, True, False),
    ('Nellik',            'Krydder', None, True, False),
    ('Stjerneanis',       'Krydder', None, True, False),
    ('Kardemomme',        'Krydder', None, True, False),
    ('Allehånde',         'Krydder', None, True, False),
    ('Safran',            'Krydder', None, True, False),
    ('Sitronpepper',      'Krydder', None, True, False),
    ('Merian',            'Krydder', None, True, False),

    # ── Frysevarer ──────────────────────────────────────────────────────────
    ('Frosne grønnsaker', 'Frysevarer', 365, False, False),
    ('Frossen spinat',    'Frysevarer', 365, False, False),
    ('Frosne bringebær',  'Frysevarer', 365, False, False),
    ('Frosne blåbær',     'Frysevarer', 365, False, False),
    ('Frosne mango',      'Frysevarer', 365, False, False),
    ('Frosne mais',       'Frysevarer', 365, False, False),
    ('Frossen laks',      'Frysevarer',  90, False, False),
    ('Frosset kylling',   'Frysevarer',  90, False, False),
    ('Frosne reker',      'Frysevarer',  90, False, False),

    # ── Snacks og Gotteri ───────────────────────────────────────────────────
    ('Melkesjokolade',    'Snacks og Gotteri', None, True, False),
    ('Hvit sjokolade',    'Snacks og Gotteri', None, True, False),
    ('Nøttemiks',         'Snacks og Gotteri', None, True, False),
    ('Tørkede aprikoser', 'Snacks og Gotteri', None, True, False),
    ('Dadler',            'Snacks og Gotteri', None, True, False),
    ('Syltetøy',          'Snacks og Gotteri', None, True, False),
]


@admin.action(description='Merge selected into oldest entry (others deleted)')
def merge_ingredient_types(modeladmin, request, queryset):
    if queryset.count() < 2:
        modeladmin.message_user(
            request,
            'Select at least 2 ingredient types to merge.',
            level='warning',
        )
        return

    # Keep the oldest (lowest ID); merge everything else into it
    canonical = queryset.order_by('id').first()
    duplicates = queryset.exclude(pk=canonical.pk)
    dup_names = ', '.join(f'"{d.name}"' for d in duplicates)

    updated = 0
    for dup in duplicates:
        updated += Ingredient.objects.filter(ingredient_type=dup).update(ingredient_type=canonical)
        updated += IngredientToShop.objects.filter(ingredient_type=dup).update(ingredient_type=canonical)
        updated += PantryItem.objects.filter(ingredient_type=dup).update(ingredient_type=canonical)

    duplicates.delete()

    modeladmin.message_user(
        request,
        f'Merged {dup_names} → "{canonical.name}". {updated} reference(s) updated.',
    )

@admin.action(description='Capitalize first letter of each name')
def capitalize_ingredient_names(modeladmin, request, queryset):
    updated = 0
    for itype in queryset:
        if not itype.name:
            continue
        new_name = itype.name[0].upper() + itype.name[1:]
        if new_name != itype.name:
            if not IngredientType.objects.filter(name=new_name).exclude(pk=itype.pk).exists():
                itype.name = new_name
                itype.save()
                updated += 1
    modeladmin.message_user(request, f'Capitalized {updated} name(s).')


@admin.action(description='Translate names to Norwegian with AI')
def ai_translate_to_norwegian(modeladmin, request, queryset):
    if queryset.count() > 100:
        modeladmin.message_user(request, 'Select 100 or fewer at a time.', level='warning')
        return

    if not os.environ.get('GOOGLE_API_KEY'):
        modeladmin.message_user(request, 'GOOGLE_API_KEY is not set.', level='error')
        return

    try:
        from google import genai
    except ImportError:
        modeladmin.message_user(request, 'google-genai is not installed.', level='error')
        return

    items = [{'id': it.id, 'name': it.name} for it in queryset]

    prompt = (
        'Translate each ingredient name to Norwegian. '
        'Capitalize only the first letter. Keep the name short and clean — '
        'no extra context like "for sauce".\n'
        'Return ONLY valid JSON, no markdown:\n'
        '{"ingredients": [{"id": 1, "name": "Hvetemel"}, {"id": 2, "name": "Egg"}]}\n\n'
        f'Ingredients:\n{json.dumps(items, ensure_ascii=False)}'
    )

    try:
        client = genai.Client()
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        raw = response.text.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
        data = json.loads(raw)
    except json.JSONDecodeError:
        modeladmin.message_user(request, 'AI returned invalid JSON. Try again.', level='error')
        return
    except Exception as exc:
        modeladmin.message_user(request, f'AI request failed: {exc}', level='error')
        return

    updated = 0
    for item in data.get('ingredients', []):
        try:
            itype = IngredientType.objects.get(pk=item['id'])
        except IngredientType.DoesNotExist:
            continue
        new_name = item.get('name', '').strip()
        if new_name and new_name != itype.name:
            if not IngredientType.objects.filter(name=new_name).exclude(pk=itype.pk).exists():
                itype.name = new_name
                itype.save()
                updated += 1

    modeladmin.message_user(request, f'Translated {updated} name(s) to Norwegian.')


@admin.action(description='Find and merge duplicates with AI')
def ai_merge_duplicate_ingredients(modeladmin, request, queryset):
    if queryset.count() > 200:
        modeladmin.message_user(
            request,
            'Select 200 or fewer at a time.',
            level='warning',
        )
        return

    if not os.environ.get('GOOGLE_API_KEY'):
        modeladmin.message_user(request, 'GOOGLE_API_KEY is not set.', level='error')
        return

    try:
        from google import genai
    except ImportError:
        modeladmin.message_user(request, 'google-genai is not installed.', level='error')
        return

    items = [{'id': it.id, 'name': it.name} for it in queryset]

    prompt = (
        'You are a food expert. The list below contains ingredient names from a recipe app — '
        'many are duplicates or near-duplicates (different capitalization, language, '
        'added context like "for sauce", abbreviations, etc.).\n\n'
        'Identify groups of ingredients that refer to the same thing and should be merged. '
        'For each group pick the best canonical name (clear, lowercase, no extra context). '
        'Only include groups where there are actual duplicates — skip unique ingredients.\n\n'
        'Return ONLY valid JSON, no markdown:\n'
        '{"merges": [\n'
        '  {"keep_id": 3, "keep_name": "water", "duplicates": [\n'
        '    {"id": 7, "name": "Vann"},\n'
        '    {"id": 12, "name": "water (for sauce)"}\n'
        '  ]}\n'
        ']}\n\n'
        f'Ingredients:\n{json.dumps(items, ensure_ascii=False)}'
    )

    try:
        client = genai.Client()
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        raw = response.text.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
        data = json.loads(raw)
    except json.JSONDecodeError:
        modeladmin.message_user(request, 'AI returned invalid JSON. Try again.', level='error')
        return
    except Exception as exc:
        modeladmin.message_user(request, f'AI request failed: {exc}', level='error')
        return

    merges = data.get('merges', [])
    if not merges:
        modeladmin.message_user(request, 'AI found no duplicates in the selection.')
        return

    total_refs = 0
    summary = []

    for merge in merges:
        try:
            canonical = IngredientType.objects.get(pk=merge['keep_id'])
        except IngredientType.DoesNotExist:
            continue

        # Optionally rename to AI's preferred canonical name
        preferred_name = merge.get('keep_name', '').strip()
        if preferred_name and preferred_name != canonical.name:
            canonical.name = preferred_name
            canonical.save()

        dup_ids = [d['id'] for d in merge.get('duplicates', [])]
        dup_names = [d['name'] for d in merge.get('duplicates', [])]
        duplicates = IngredientType.objects.filter(pk__in=dup_ids)

        refs = 0
        for dup in duplicates:
            refs += Ingredient.objects.filter(ingredient_type=dup).update(ingredient_type=canonical)
            refs += IngredientToShop.objects.filter(ingredient_type=dup).update(ingredient_type=canonical)
            refs += PantryItem.objects.filter(ingredient_type=dup).update(ingredient_type=canonical)
        duplicates.delete()

        total_refs += refs
        summary.append(f'"{canonical.name}" ← {", ".join(f"{chr(34)}{n}{chr(34)}" for n in dup_names)}')

    modeladmin.message_user(
        request,
        f'Merged {len(merges)} group(s), {total_refs} reference(s) updated. '
        + ' | '.join(summary),
    )


@admin.action(description='Fill missing data with AI (category, staple flags, shelf life)')
def ai_enrich_ingredient_types(modeladmin, request, queryset):
    if queryset.count() > 50:
        modeladmin.message_user(
            request,
            'Select 50 or fewer at a time to avoid timeouts.',
            level='warning',
        )
        return

    if not os.environ.get('GOOGLE_API_KEY'):
        modeladmin.message_user(request, 'GOOGLE_API_KEY is not set.', level='error')
        return

    try:
        from google import genai
    except ImportError:
        modeladmin.message_user(request, 'google-genai is not installed.', level='error')
        return

    tag_names = list(Tagg.objects.values_list('name', flat=True))
    items = [{'id': it.id, 'name': it.name} for it in queryset]

    prompt = (
        'You are a food expert. For each ingredient below, fill in the correct data.\n\n'
        f'Available categories: {", ".join(tag_names) if tag_names else "none"}\n\n'
        'Rules:\n'
        '- tagg: best matching category from the list above, or null if none fits\n'
        '- is_staple: true for common pantry staples kept stocked long-term (salt, oil, flour, sugar, spices)\n'
        '- is_always_available: true ONLY for things never bought (water, tap water)\n'
        '- shelf_life_days: days until typical spoilage at home; null for indefinitely shelf-stable items '
        '(salt, sugar, spices, canned goods) or staples\n\n'
        'Return ONLY valid JSON, no markdown:\n'
        '{"ingredients": [\n'
        '  {"id": 1, "tagg": "Vegetables", "is_staple": false, "is_always_available": false, "shelf_life_days": 7},\n'
        '  {"id": 2, "tagg": null, "is_staple": true, "is_always_available": false, "shelf_life_days": null}\n'
        ']}\n\n'
        f'Ingredients:\n{json.dumps(items, ensure_ascii=False)}'
    )

    try:
        client = genai.Client()
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        raw = response.text.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
        data = json.loads(raw)
    except json.JSONDecodeError:
        modeladmin.message_user(request, 'AI returned invalid JSON. Try again.', level='error')
        return
    except Exception as exc:
        modeladmin.message_user(request, f'AI request failed: {exc}', level='error')
        return

    tag_map = {t.name.lower(): t for t in Tagg.objects.all()}
    updated = 0

    for item_data in data.get('ingredients', []):
        try:
            itype = IngredientType.objects.get(pk=item_data['id'])
        except IngredientType.DoesNotExist:
            continue

        tagg_name = item_data.get('tagg')
        if tagg_name:
            itype.tagg = tag_map.get(tagg_name.lower())

        itype.is_staple = bool(item_data.get('is_staple', itype.is_staple))
        itype.is_always_available = bool(item_data.get('is_always_available', itype.is_always_available))

        shelf = item_data.get('shelf_life_days')
        if shelf is not None:
            itype.shelf_life_days = int(shelf)

        itype.save()
        updated += 1

    modeladmin.message_user(request, f'AI enriched {updated} ingredient type(s).')


# Register your models here.


class IngredientAdminInline(admin.TabularInline):
    model = Ingredient
    fields = ('ingredient_type', 'measurment')
    # Django automatically adds a + popup button next to ingredient_type
    # so new ingredient types can be created without leaving the recipe page


class InstructionAdminInline(admin.TabularInline):
    model = Instruction


class InfoAdmin(admin.ModelAdmin):
    inlines = (IngredientAdminInline, InstructionAdminInline,)
    filter_horizontal = ('recipe_tags',)


@admin.register(IngredientType)
class IngredientTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'tagg', 'shelf_life_days', 'is_staple', 'is_always_available')
    list_filter = ('tagg', 'is_staple', 'is_always_available')
    search_fields = ('name',)
    ordering = ('name',)
    change_list_template = 'admin/recipes/ingredienttype/change_list.html'
    actions = [
        capitalize_ingredient_names,
        ai_translate_to_norwegian,
        ai_merge_duplicate_ingredients,
        ai_enrich_ingredient_types,
        merge_ingredient_types,
    ]

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'seed/',
                self.admin_site.admin_view(self.seed_view),
                name='recipes_ingredienttype_seed',
            ),
        ]
        return custom + urls

    def seed_view(self, request):
        """POST handler for the 🌱 Seed button in the changelist toolbar."""
        if request.method != 'POST':
            return redirect('..')

        tag_cache = {t.name: t for t in Tagg.objects.all()}
        created = 0
        skipped = 0

        for name, tagg_name, shelf_life, is_staple, is_always_avail in _SEED_DATA:
            tagg = tag_cache.get(tagg_name)
            _, was_created = IngredientType.objects.get_or_create(
                name=name,
                defaults={
                    'tagg': tagg,
                    'shelf_life_days': shelf_life,
                    'is_staple': is_staple,
                    'is_always_available': is_always_avail,
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.message_user(
            request,
            f'Seeding fullført: {created} opprettet, {skipped} fantes allerede.',
        )
        return redirect('..')


class DinnerComponentInline(admin.TabularInline):
    model = DinnerComponent
    fields = ('recipe', 'role', 'order', 'default_selected')
    extra = 1


@admin.register(Dinner)
class DinnerAdmin(admin.ModelAdmin):
    inlines = (DinnerComponentInline,)
    list_display = ('title', 'pub_date')


admin.site.register(Info, InfoAdmin)
admin.site.register(Tagg)
admin.site.register(RecipeTag)
admin.site.register(PantryItem)


@admin.register(RecipeSource)
class RecipeSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_url', 'is_active')
    list_filter = ('is_active',)
    help_texts = {
        'search_url_pattern': (
            'Use {query} as a placeholder for the search term. '
            'Example: https://www.allrecipes.com/search?q={query}'
        )
    }
