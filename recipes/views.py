from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.template import loader
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views import generic
from django.http import HttpResponseRedirect


from django.contrib.auth.models import User
from .models import Info, Tagg, Ingredient, IngredientForm, IngredientToShop

# Create your views here.


def index(request):
    latest_info_list = Info.objects.order_by('-pub_date')[:5]
    #template = loader.get_template('recipes/index.html')
    #output = ', '.join([q.title for q in latest_info_list])
    context = {'latest_info_list': latest_info_list}
    return render(request, 'recipes/index.html', context)
    #return HttpResponse(output)


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
    
    



class SignUpView(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('/recipes/accounts/login/')
    template_name = 'registration/signup.html'
