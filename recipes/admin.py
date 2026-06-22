import os
import json
from django.contrib import admin
from recipes.models import (
    Ingredient, Instruction, Tagg, RecipeTag, PantryItem,
    IngredientType, Dinner, DinnerComponent, RecipeSource,
    IngredientToShop,
)
from django.contrib.auth.models import User

from .models import Info


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
    actions = [merge_ingredient_types, ai_enrich_ingredient_types]


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
