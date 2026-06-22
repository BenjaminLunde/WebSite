import os
import json
from collections import defaultdict

from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.template import loader
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views import generic
from django.http import HttpResponseRedirect


from django.contrib.auth.models import User
from .models import (
    Info, Tagg, RecipeTag, Ingredient, IngredientType, IngredientForm,
    Instruction, IngredientToShop, PantryItem, Dinner, DinnerComponent, RecipeSource,
)
from .units import UNITS, parse_amount, format_amount, add_amounts, subtract_amounts

# Create your views here.


def index(request):
    tag_id = request.GET.get('tag')
    all_tags = RecipeTag.objects.order_by('name')
    # Only staff/superusers can see draft recipes
    base_qs = Info.objects.all() if (request.user.is_authenticated and request.user.is_staff) \
        else Info.objects.filter(is_draft=False)
    if tag_id:
        recipe_list = base_qs.filter(recipe_tags__id=tag_id).order_by('-pub_date')
        selected_tag = RecipeTag.objects.filter(id=tag_id).first()
    else:
        recipe_list = base_qs.order_by('-pub_date')
        selected_tag = None
    context = {
        'latest_info_list': recipe_list,
        'all_tags': all_tags,
        'selected_tag': selected_tag,
    }
    return render(request, 'recipes/index.html', context)


def dinners(request):
    dinner_list = Dinner.objects.order_by('-pub_date').prefetch_related('components')
    return render(request, 'recipes/dinners.html', {'dinner_list': dinner_list})


def get_one(request, info_id):
    info = get_object_or_404(Info, pk=info_id)
    dinners = Dinner.objects.filter(
        components__recipe=info
    ).prefetch_related('components__recipe__recipe_tags').distinct()
    pantry_type_ids = set()
    if request.user.is_authenticated:
        pantry_type_ids = set(
            PantryItem.objects.filter(user=request.user)
            .values_list('ingredient_type_id', flat=True)
        )
    return render(request, 'recipes/info.html', {
        'info': info,
        'dinners': dinners,
        'pantry_type_ids': pantry_type_ids,
    })


def account(request):
    return render(request, 'recipes/account.html', {})


def _add_to_shop_list(user, itype, new_amount):
    """
    Add or combine an ingredient into the user's shopping list.

    If the user already has that IngredientType on the list, the amounts are
    combined with add_amounts().  When units are incompatible (e.g. "stk" and
    "g"), a second separate row is created instead of silently dropping data.
    """
    existing = IngredientToShop.objects.filter(shopper=user, ingredient_type=itype).first()
    if existing:
        pq, pu = parse_amount(existing.amount)
        nq, nu = parse_amount(new_amount)
        if pq is not None and nq is not None:
            rq, ru = add_amounts(pq, pu, nq, nu)
            if rq is not None:
                existing.amount = format_amount(rq, ru)
                existing.save()
                return
        # Units incompatible or unparseable — fall through to create a second row
    IngredientToShop.objects.create(shopper=user, ingredient_type=itype, amount=new_amount)


def shopping(request):
    if request.user.is_authenticated:

        current_user = request.user

        if request.method == 'POST':
            itype = IngredientType.objects.filter(pk=request.POST.get('ingredient_type')).first()
            raw_qty = request.POST.get('qty', '').strip()
            unit = request.POST.get('unit', '').strip()
            if itype and raw_qty and unit in UNITS:
                try:
                    from decimal import Decimal
                    qty = Decimal(raw_qty)
                    new_amount = format_amount(qty, unit)
                except Exception:
                    new_amount = ''
                if new_amount:
                    _add_to_shop_list(current_user, itype, new_amount)

        tagg_list = Tagg.objects.order_by('id')
        ingredient_type_list = IngredientType.objects.order_by('name')
        shop_qs = IngredientToShop.objects.filter(shopper=current_user).select_related(
            'ingredient_type__tagg'
        )

        # Group items by tagg (only include categories that have items)
        items_by_tagg = defaultdict(list)
        for item in shop_qs:
            tagg = item.tagg
            if tagg:
                items_by_tagg[tagg.id].append(item)

        tagg_with_items = [
            (tagg, items_by_tagg[tagg.id])
            for tagg in tagg_list
            if items_by_tagg[tagg.id]
        ]

        context = {
            'tagg_with_items': tagg_with_items,
            'ingredient_type_list': ingredient_type_list,
            'has_items': shop_qs.exists(),
            'units': UNITS,
        }
        return render(request, 'recipes/shopping.html', context)
    else:
        return HttpResponseRedirect("/recipes/")


def delete_shop(request, ingredientToShop_id=None):
    if request.user.is_authenticated:
        obj = get_object_or_404(IngredientToShop, id=ingredientToShop_id)
        if(request.user == obj.shopper):
            obj.delete()
    return HttpResponseRedirect("/recipes/shopping/")

def delete_all(request):
    if request.user.is_authenticated:
        shop_list = IngredientToShop.objects.filter(shopper = request.user)
        for item in shop_list:
            item.delete()
    return HttpResponseRedirect("/recipes/shopping/")


def add_to_shop(request):
    if request.user.is_authenticated:
        current_user = request.user
        if request.method == 'POST':
            ingredients = request.POST
            list_ing = iter(ingredients)
            next(list_ing)  # skip csrfmiddlewaretoken
            for item in list_ing:
                ing = Ingredient.objects.select_related('ingredient_type').filter(
                    pk=request.POST[item]
                ).first()
                if ing and ing.ingredient_type:
                    _add_to_shop_list(current_user, ing.ingredient_type, ing.measurment)

    return HttpResponseRedirect("/recipes/shopping/")
    
    



def pantry(request):
    if request.user.is_authenticated:
        current_user = request.user

        if request.method == 'POST':
            itype = IngredientType.objects.filter(pk=request.POST.get('ingredient_type')).first()
            raw_qty = request.POST.get('qty', '').strip()
            unit = request.POST.get('unit', '').strip()
            if itype and raw_qty and unit in UNITS:
                try:
                    from decimal import Decimal
                    new_qty = Decimal(raw_qty)
                except Exception:
                    new_qty = None
                if new_qty is not None and new_qty > 0:
                    new_amount = format_amount(new_qty, unit)
                    existing = PantryItem.objects.filter(
                        user=current_user, ingredient_type=itype
                    ).first()
                    if existing:
                        pq, pu = parse_amount(existing.amount)
                        if pq is not None:
                            rq, ru = add_amounts(pq, pu, new_qty, unit)
                            if rq is not None:
                                existing.amount = format_amount(rq, ru)
                                existing.save()
                            else:
                                # Incompatible units — create a new entry
                                PantryItem.objects.create(
                                    user=current_user, ingredient_type=itype, amount=new_amount
                                )
                        else:
                            # Existing amount not parseable — overwrite it
                            existing.amount = new_amount
                            existing.save()
                    else:
                        PantryItem.objects.create(
                            user=current_user, ingredient_type=itype, amount=new_amount
                        )

        tagg_list = Tagg.objects.order_by('id')
        ingredient_type_list = IngredientType.objects.order_by('name')
        pantry_list = PantryItem.objects.filter(user=current_user).select_related(
            'ingredient_type__tagg'
        ).order_by('added_date')
        context = {
            'tagg_list': tagg_list,
            'ingredient_type_list': ingredient_type_list,
            'pantry_list': pantry_list,
            'units': UNITS,
        }
        return render(request, 'recipes/pantry.html', context)
    else:
        return HttpResponseRedirect('/recipes/')


def add_to_pantry(request):
    """Move a shopping list item into the pantry, then remove it from shopping."""
    if request.user.is_authenticated and request.method == 'POST':
        shop_item_id = request.POST.get('shop_item_id')
        obj = IngredientToShop.objects.filter(id=shop_item_id, shopper=request.user).first()
        if obj and obj.ingredient_type:
            itype = obj.ingredient_type
            new_amount = obj.amount
            new_qty, new_unit = parse_amount(new_amount)

            existing = PantryItem.objects.filter(
                user=request.user, ingredient_type=itype
            ).first()

            if existing and new_qty is not None:
                pq, pu = parse_amount(existing.amount)
                if pq is not None:
                    rq, ru = add_amounts(pq, pu, new_qty, new_unit)
                    if rq is not None:
                        existing.amount = format_amount(rq, ru)
                        existing.save()
                        obj.delete()
                        return HttpResponseRedirect('/recipes/pantry/')
            # Fallback: create a new pantry entry (old behaviour)
            PantryItem.objects.create(
                user=request.user,
                ingredient_type=itype,
                amount=new_amount,
            )
            obj.delete()
    return HttpResponseRedirect('/recipes/pantry/')


def add_checked_to_pantry(request):
    """Move all checked shopping items to pantry."""
    if request.user.is_authenticated and request.method == 'POST':
        shop_ids = request.POST.getlist('shop_ids')
        for shop_id in shop_ids:
            obj = IngredientToShop.objects.filter(id=shop_id, shopper=request.user).first()
            if not obj or not obj.ingredient_type:
                continue

            itype = obj.ingredient_type
            new_amount = obj.amount
            new_qty_parsed, new_unit_parsed = parse_amount(new_amount)

            existing = PantryItem.objects.filter(
                user=request.user, ingredient_type=itype
            ).first()

            if existing and new_qty_parsed is not None:
                pq, pu = parse_amount(existing.amount)
                if pq is not None:
                    rq, ru = add_amounts(pq, pu, new_qty_parsed, new_unit_parsed)
                    if rq is not None:
                        existing.amount = format_amount(rq, ru)
                        existing.save()
                        obj.delete()
                        continue

            # Fallback: create a fresh pantry entry (incompatible units or no existing item)
            PantryItem.objects.create(
                user=request.user,
                ingredient_type=itype,
                amount=new_amount,
            )
            obj.delete()

    return HttpResponseRedirect('/recipes/pantry/')


def delete_pantry_item(request, pantry_item_id=None):
    if request.user.is_authenticated:
        obj = get_object_or_404(PantryItem, id=pantry_item_id)
        if request.user == obj.user:
            obj.delete()
    return HttpResponseRedirect('/recipes/pantry/')


def delete_all_pantry(request):
    if request.user.is_authenticated:
        PantryItem.objects.filter(user=request.user).delete()
    return HttpResponseRedirect('/recipes/pantry/')


def delete_selected_pantry(request):
    """Delete pantry items the user checked."""
    if request.user.is_authenticated and request.method == 'POST':
        ids = request.POST.getlist('pantry_ids')
        PantryItem.objects.filter(user=request.user, id__in=ids).delete()
    return HttpResponseRedirect('/recipes/pantry/')


def remove_used_ingredients(request):
    """Subtract selected recipe ingredient amounts from the user's pantry."""
    if request.user.is_authenticated and request.method == 'POST':
        ingredients = request.POST
        list_ing = iter(ingredients)
        next(list_ing)  # skip csrf token
        for item in list_ing:
            ingredient = Ingredient.objects.filter(pk=request.POST[item]).first()
            if ingredient and ingredient.ingredient_type:
                pantry_item = PantryItem.objects.filter(
                    user=request.user,
                    ingredient_type=ingredient.ingredient_type,
                ).first()
                if pantry_item is None:
                    continue
                pq, pu = parse_amount(pantry_item.amount)
                rq, ru = parse_amount(ingredient.measurment)
                if pq is not None and rq is not None:
                    sq, su = subtract_amounts(pq, pu, rq, ru)
                    if sq is not None and sq > 0:
                        pantry_item.amount = format_amount(sq, su)
                        pantry_item.save()
                    else:
                        pantry_item.delete()
                else:
                    # Amounts not parseable — fall back to deleting the entry
                    pantry_item.delete()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/recipes/'))


def combined_dinner(request, info_id):
    """
    Show a combined view of a main recipe + selected related recipes.
    POST: receive checked related-recipe IDs and display the merged result.
    GET: redirect back to the recipe.
    """
    main = get_object_or_404(Info, pk=info_id)
    if request.method != 'POST':
        return HttpResponseRedirect(f'/recipes/{info_id}/')

    # Collect which related recipes the user selected
    selected_ids = request.POST.getlist('related_ids')
    related = list(Info.objects.filter(id__in=selected_ids).prefetch_related(
        'ingredient_set__ingredient_type', 'instruction_set'
    ))

    context = {
        'main': main,
        'selected': related,
    }
    return render(request, 'recipes/combined_dinner.html', context)


def add_combined_to_shop(request):
    """Add ingredients from multiple recipes (main + selected sides) to the shopping list."""
    if not request.user.is_authenticated or request.method != 'POST':
        return HttpResponseRedirect('/recipes/shopping/')

    recipe_ids = request.POST.getlist('recipe_ids')
    for recipe_id in recipe_ids:
        recipe = Info.objects.filter(pk=recipe_id).first()
        if recipe:
            for ingredient in recipe.ingredient_set.select_related('ingredient_type').all():
                if ingredient.ingredient_type:
                    _add_to_shop_list(request.user, ingredient.ingredient_type, ingredient.measurment)
    return HttpResponseRedirect('/recipes/shopping/')


def meal_planner(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/recipes/')

    suggestions = []
    reasoning = ''
    user_request = ''
    error = ''

    if request.method == 'POST':
        user_request = request.POST.get('user_request', '').strip()
        if user_request:
            from .ai_planner import suggest_meals
            recipes = Info.objects.prefetch_related(
                'recipe_tags', 'ingredient_set__ingredient_type'
            ).all()
            pantry_items = list(
                PantryItem.objects.filter(user=request.user)
                .select_related('ingredient_type')
                .order_by('added_date')
            )

            ids, reasoning, error = suggest_meals(user_request, recipes, pantry_items)
            if ids:
                id_order = {sid: idx for idx, sid in enumerate(ids)}
                suggestions = list(Info.objects.filter(id__in=ids))
                suggestions.sort(key=lambda r: id_order.get(r.id, 999))

    context = {
        'suggestions': suggestions,
        'reasoning': reasoning,
        'user_request': user_request,
        'error': error,
    }
    return render(request, 'recipes/meal_planner.html', context)


def dinner_detail(request, dinner_id):
    """Show a dinner page with its components as selectable checkboxes."""
    dinner = get_object_or_404(Dinner, pk=dinner_id)
    components_qs = dinner.components.select_related('recipe').prefetch_related(
        'recipe__recipe_tags'
    ).order_by('order', 'id')

    # Group by role, preserving the order in which each role first appears.
    # The role whose first component has the lowest 'order' number comes first.
    role_groups = {}
    role_order = []
    for comp in components_qs:
        if comp.role not in role_groups:
            role_groups[comp.role] = []
            role_order.append(comp.role)
        role_groups[comp.role].append(comp)

    grouped = [(role, role_groups[role]) for role in role_order]
    return render(request, 'recipes/dinner.html', {'dinner': dinner, 'grouped': grouped})


def dinner_combined(request, dinner_id):
    """Render a combined view of the dinner components the user selected."""
    dinner = get_object_or_404(Dinner, pk=dinner_id)
    if request.method != 'POST':
        return HttpResponseRedirect(f'/recipes/dinners/{dinner_id}/')
    selected_ids = request.POST.getlist('component_ids')
    components = DinnerComponent.objects.filter(
        id__in=selected_ids, dinner=dinner
    ).select_related('recipe').prefetch_related(
        'recipe__ingredient_set__ingredient_type',
        'recipe__instruction_set',
    )
    pantry_type_ids = set()
    if request.user.is_authenticated:
        pantry_type_ids = set(
            PantryItem.objects.filter(user=request.user)
            .values_list('ingredient_type_id', flat=True)
        )
    return render(request, 'recipes/dinner_combined.html', {
        'dinner': dinner,
        'components': components,
        'pantry_type_ids': pantry_type_ids,
    })


def add_dinner_to_shop(request):
    """Add all ingredients from selected dinner components to the shopping list."""
    if not request.user.is_authenticated or request.method != 'POST':
        return HttpResponseRedirect('/recipes/shopping/')
    component_ids = request.POST.getlist('component_ids')
    components = DinnerComponent.objects.filter(
        id__in=component_ids
    ).select_related('recipe')
    for comp in components:
        for ingredient in comp.recipe.ingredient_set.select_related('ingredient_type').all():
            if ingredient.ingredient_type:
                _add_to_shop_list(request.user, ingredient.ingredient_type, ingredient.measurment)
    return HttpResponseRedirect('/recipes/shopping/')


def edit_recipe(request, info_id):
    """
    Staff-only: edit a recipe directly on a formatted page.
    Uses the same two-column layout as the recipe view so you can see
    what you're changing while you edit it.
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponseRedirect(f'/recipes/{info_id}/')

    recipe = get_object_or_404(Info, pk=info_id)

    if request.method == 'POST':
        # ── Basic fields ──────────────────────────────────────────────────────
        recipe.title      = request.POST.get('title',      recipe.title).strip()
        recipe.intro      = request.POST.get('intro',      recipe.intro).strip()
        recipe.time       = request.POST.get('time',       recipe.time).strip()
        try:
            recipe.servings   = int(request.POST.get('servings',   recipe.servings))
            recipe.difficulty = int(request.POST.get('difficulty', recipe.difficulty))
        except (ValueError, TypeError):
            pass
        recipe.save()

        # ── Tags ──────────────────────────────────────────────────────────────
        tag_ids = request.POST.getlist('tags')
        recipe.recipe_tags.set(RecipeTag.objects.filter(id__in=tag_ids))

        # ── Ingredients ───────────────────────────────────────────────────────
        # Form sends: ing_count, then for each index i:
        #   ing_id_i   (empty = new row), ing_name_i, ing_amount_i, ing_delete_i
        ing_count = int(request.POST.get('ing_count', 0))
        for i in range(ing_count):
            ing_id     = request.POST.get(f'ing_id_{i}',     '').strip()
            ing_name   = request.POST.get(f'ing_name_{i}',   '').strip()
            ing_amount = request.POST.get(f'ing_amount_{i}', '').strip()
            ing_delete = request.POST.get(f'ing_delete_{i}', '') == '1'

            if ing_id:
                obj = Ingredient.objects.filter(pk=ing_id, info=recipe).first()
                if obj:
                    if ing_delete:
                        obj.delete()
                    elif ing_name:
                        itype, _ = IngredientType.objects.get_or_create(name=ing_name)
                        obj.ingredient_type = itype
                        obj.measurment = ing_amount
                        obj.save()
            elif ing_name and not ing_delete:
                itype, _ = IngredientType.objects.get_or_create(name=ing_name)
                Ingredient.objects.create(info=recipe, ingredient_type=itype, measurment=ing_amount)

        # ── Instructions ──────────────────────────────────────────────────────
        inst_count = int(request.POST.get('inst_count', 0))
        for i in range(inst_count):
            inst_id     = request.POST.get(f'inst_id_{i}',     '').strip()
            inst_text   = request.POST.get(f'inst_text_{i}',   '').strip()
            inst_delete = request.POST.get(f'inst_delete_{i}', '') == '1'

            if inst_id:
                obj = Instruction.objects.filter(pk=inst_id, info=recipe).first()
                if obj:
                    if inst_delete:
                        obj.delete()
                    elif inst_text:
                        obj.text = inst_text
                        obj.save()
            elif inst_text and not inst_delete:
                Instruction.objects.create(info=recipe, text=inst_text)

        return HttpResponseRedirect(f'/recipes/{info_id}/')

    # ── GET ───────────────────────────────────────────────────────────────────
    all_tags = RecipeTag.objects.order_by('name')
    selected_tag_ids = set(recipe.recipe_tags.values_list('id', flat=True))

    context = {
        'recipe':           recipe,
        'all_tags':         all_tags,
        'selected_tag_ids': selected_tag_ids,
        'ingredients':      list(recipe.ingredient_set.all()),
        'instructions':     list(recipe.instruction_set.all()),
    }
    return render(request, 'recipes/edit_recipe.html', context)


def log_cook(request, info_id):
    """
    POST: update the cook-log fields (last_cooked, score, revision_notes) on a recipe.
    Only authenticated users can log cooks.
    """
    if not request.user.is_authenticated or request.method != 'POST':
        return HttpResponseRedirect(f'/recipes/{info_id}/')

    import datetime
    recipe = get_object_or_404(Info, pk=info_id)

    raw_date = request.POST.get('last_cooked', '').strip()
    raw_score = request.POST.get('score', '').strip()
    notes = request.POST.get('revision_notes', '').strip()

    # Date
    if raw_date:
        try:
            recipe.last_cooked = datetime.date.fromisoformat(raw_date)
        except ValueError:
            pass
    else:
        recipe.last_cooked = datetime.date.today()

    # Score (1–10)
    if raw_score:
        try:
            score_val = int(raw_score)
            if 1 <= score_val <= 10:
                recipe.score = score_val
        except ValueError:
            pass

    recipe.revision_notes = notes
    recipe.save()
    return HttpResponseRedirect(f'/recipes/{info_id}/')


def import_recipe(request):
    """
    Superuser-only page to import a recipe from a trusted cooking website.
    GET:  show the import form (sources list + URL/search input).
    POST: run the import and redirect to the new draft recipe.
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponseRedirect('/recipes/')

    sources = RecipeSource.objects.filter(is_active=True)
    error = ''
    preview = None
    source_url = ''

    if request.method == 'POST':
        from .recipe_importer import import_from_url, search_and_import, create_draft_recipe

        direct_url = request.POST.get('direct_url', '').strip()
        search_query = request.POST.get('search_query', '').strip()

        if direct_url:
            data, source_url, error = import_from_url(direct_url)
        elif search_query:
            data, source_url, error = search_and_import(search_query, sources)
        else:
            error = 'Please enter a URL or a search term.'
            data = None

        if data and not error:
            recipe = create_draft_recipe(data)
            return HttpResponseRedirect(f'/recipes/{recipe.id}/')

        preview = data  # Show partial preview even on error

    context = {
        'sources': sources,
        'error': error,
        'preview': preview,
        'source_url': source_url,
    }
    return render(request, 'recipes/import_recipe.html', context)


def publish_recipe(request, info_id):
    """Superuser only: toggle a recipe between draft and published."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponseRedirect('/recipes/')
    if request.method == 'POST':
        recipe = get_object_or_404(Info, pk=info_id)
        recipe.is_draft = not recipe.is_draft
        recipe.save()
    return HttpResponseRedirect(f'/recipes/{info_id}/')


class SignUpView(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('recipes:login')
    template_name = 'registration/signup.html'
