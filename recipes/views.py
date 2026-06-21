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
from .models import Info, Tagg, RecipeTag, Ingredient, IngredientForm, IngredientToShop, PantryItem

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
    context = {
        'latest_info_list': recipe_list,
        'all_tags': all_tags,
        'selected_tag': selected_tag,
    }
    return render(request, 'recipes/index.html', context)


def get_one(request, info_id):
    info = get_object_or_404(Info, pk=info_id)
    return render(request, 'recipes/info.html', {'info': info})


def account(request):
    return render(request, 'recipes/account.html', {})


def shopping(request):
    if request.user.is_authenticated:

        current_user = request.user

        if request.method == 'POST':
            tagg = Tagg.objects.get(pk=request.POST['tagg'])
            name = request.POST['name']
            amount = request.POST['measurment']

            ingredient = Ingredient()
            ingredient.tagg = tagg
            ingredient.name = name
            ingredient.measurment = amount
            ingredient.save()

            toShop = IngredientToShop()
            toShop.shopper = current_user
            toShop.ingredient = ingredient
            toShop.save()

        tagg_list = Tagg.objects.order_by('id')
        shop_list = IngredientToShop.objects.filter(shopper=current_user)
        context = {'tagg_list': tagg_list, 'shop_list': shop_list, }
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
            tagg_id = request.POST.get('tagg')
            name = request.POST.get('name', '').strip()
            amount = request.POST.get('amount', '').strip()
            if name and amount:
                tagg = Tagg.objects.filter(pk=tagg_id).first()
                PantryItem.objects.create(
                    user=current_user,
                    name=name,
                    amount=amount,
                    tagg=tagg,
                )

        tagg_list = Tagg.objects.order_by('id')
        pantry_list = PantryItem.objects.filter(user=current_user).order_by('added_date')
        context = {'tagg_list': tagg_list, 'pantry_list': pantry_list}
        return render(request, 'recipes/pantry.html', context)
    else:
        return HttpResponseRedirect('/recipes/')


def add_to_pantry(request):
    """Move a shopping list item into the pantry, then remove it from shopping."""
    if request.user.is_authenticated and request.method == 'POST':
        shop_item_id = request.POST.get('shop_item_id')
        obj = IngredientToShop.objects.filter(id=shop_item_id, shopper=request.user).first()
        if obj:
            PantryItem.objects.create(
                user=request.user,
                name=obj.ingredient.name,
                amount=obj.ingredient.measurment,
                tagg=obj.ingredient.tagg,
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


def remove_used_ingredients(request):
    """Remove selected recipe ingredients from the user's pantry by name match."""
    if request.user.is_authenticated and request.method == 'POST':
        ingredients = request.POST
        list_ing = iter(ingredients)
        next(list_ing)  # skip csrf token
        for item in list_ing:
            ingredient = Ingredient.objects.filter(pk=request.POST[item]).first()
            if ingredient:
                # Case-insensitive name match against pantry items
                PantryItem.objects.filter(
                    user=request.user,
                    name__iexact=ingredient.name,
                ).delete()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/recipes/'))


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
            recipes = Info.objects.prefetch_related('recipe_tags', 'ingredient_set').all()
            pantry_items = list(PantryItem.objects.filter(user=request.user).order_by('added_date'))

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


class SignUpView(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('recipes:login')
    template_name = 'registration/signup.html'
