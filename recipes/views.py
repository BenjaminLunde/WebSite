import os
import json

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
    IngredientToShop, PantryItem, Dinner, DinnerComponent,
)

# Create your views here.


def index(request):
    tag_id = request.GET.get('tag')
    all_tags = RecipeTag.objects.order_by('name')
    if tag_id:
        recipe_list = Info.objects.filter(recipe_tags__id=tag_id).order_by('-pub_date')
        selected_tag = RecipeTag.objects.filter(id=tag_id).first()
    else:
        recipe_list = Info.objects.order_by('-pub_date')
        selected_tag = None
    dinner_list = Dinner.objects.order_by('-pub_date').prefetch_related('components')
    context = {
        'latest_info_list': recipe_list,
        'all_tags': all_tags,
        'selected_tag': selected_tag,
        'dinner_list': dinner_list,
    }
    return render(request, 'recipes/index.html', context)


def get_one(request, info_id):
    info = get_object_or_404(Info, pk=info_id)
    # Find dinners that include this recipe as a component
    dinners = Dinner.objects.filter(
        components__recipe=info
    ).prefetch_related(
        'components__recipe__recipe_tags'
    ).distinct()
    return render(request, 'recipes/info.html', {'info': info, 'dinners': dinners})


def account(request):
    return render(request, 'recipes/account.html', {})


def shopping(request):
    if request.user.is_authenticated:

        current_user = request.user

        if request.method == 'POST':
            itype = IngredientType.objects.filter(pk=request.POST.get('ingredient_type')).first()
            amount = request.POST.get('measurment', '').strip()
            if itype and amount:
                ingredient = Ingredient()
                ingredient.ingredient_type = itype
                ingredient.measurment = amount
                ingredient.save()

                toShop = IngredientToShop()
                toShop.shopper = current_user
                toShop.ingredient = ingredient
                toShop.save()

        tagg_list = Tagg.objects.order_by('id')
        ingredient_type_list = IngredientType.objects.order_by('name')
        shop_list = IngredientToShop.objects.filter(shopper=current_user).select_related(
            'ingredient__ingredient_type__tagg'
        )
        context = {
            'tagg_list': tagg_list,
            'ingredient_type_list': ingredient_type_list,
            'shop_list': shop_list,
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
            next(list_ing)
            for item in list_ing:
                toShop = IngredientToShop()
                toShop.shopper = current_user
                toShop.ingredient = Ingredient.objects.get(pk = request.POST[item])
                toShop.save()

    return HttpResponseRedirect("/recipes/shopping/")
    
    



def pantry(request):
    if request.user.is_authenticated:
        current_user = request.user

        if request.method == 'POST':
            itype = IngredientType.objects.filter(pk=request.POST.get('ingredient_type')).first()
            amount = request.POST.get('amount', '').strip()
            if itype and amount:
                PantryItem.objects.create(
                    user=current_user,
                    ingredient_type=itype,
                    amount=amount,
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
        }
        return render(request, 'recipes/pantry.html', context)
    else:
        return HttpResponseRedirect('/recipes/')


def add_to_pantry(request):
    """Move a shopping list item into the pantry, then remove it from shopping."""
    if request.user.is_authenticated and request.method == 'POST':
        shop_item_id = request.POST.get('shop_item_id')
        obj = IngredientToShop.objects.filter(id=shop_item_id, shopper=request.user).first()
        if obj and obj.ingredient.ingredient_type:
            PantryItem.objects.create(
                user=request.user,
                ingredient_type=obj.ingredient.ingredient_type,
                amount=obj.ingredient.measurment,
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
    """Remove selected recipe ingredients from the user's pantry by ingredient_type FK."""
    if request.user.is_authenticated and request.method == 'POST':
        ingredients = request.POST
        list_ing = iter(ingredients)
        next(list_ing)  # skip csrf token
        for item in list_ing:
            ingredient = Ingredient.objects.filter(pk=request.POST[item]).first()
            if ingredient and ingredient.ingredient_type:
                PantryItem.objects.filter(
                    user=request.user,
                    ingredient_type=ingredient.ingredient_type,
                ).delete()
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
            for ingredient in recipe.ingredient_set.all():
                IngredientToShop.objects.create(
                    shopper=request.user,
                    ingredient=ingredient,
                )
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
    return render(request, 'recipes/dinner_combined.html', {
        'dinner': dinner,
        'components': components,
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
        for ingredient in comp.recipe.ingredient_set.all():
            IngredientToShop.objects.create(shopper=request.user, ingredient=ingredient)
    return HttpResponseRedirect('/recipes/shopping/')


class SignUpView(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('recipes:login')
    template_name = 'registration/signup.html'
