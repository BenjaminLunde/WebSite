from django.urls import path, include


from . import views

app_name = 'recipes'
urlpatterns = [
    path('', views.dinners, name='index'),
    path('recipes/', views.index, name='recipes'),
    path('<int:info_id>/', views.get_one, name="get_one"),
    path('shopping/', views.shopping, name="shopping"),
    path('accounts/', include('django.contrib.auth.urls')),
    path('account/', views.account, name="account"),
    path('delete/<int:ingredientToShop_id>', views.delete_shop, name='delete'),
    path('delete_all/', views.delete_all, name='delete_all'),
    path('add_to_shop/', views.add_to_shop, name='add_to_shop'),
    path('pantry/', views.pantry, name='pantry'),
    path('pantry/add/', views.add_to_pantry, name='add_to_pantry'),
    path('pantry/delete/<int:pantry_item_id>/', views.delete_pantry_item, name='delete_pantry_item'),
    path('pantry/delete_all/', views.delete_all_pantry, name='delete_all_pantry'),
    path('pantry/delete_selected/', views.delete_selected_pantry, name='delete_selected_pantry'),
    path('remove_used/', views.remove_used_ingredients, name='remove_used'),
    path('meal-planner/', views.meal_planner, name='meal_planner'),
    path('<int:info_id>/combined/', views.combined_dinner, name='combined_dinner'),
    path('add_combined_to_shop/', views.add_combined_to_shop, name='add_combined_to_shop'),
    path('dinners/<int:dinner_id>/', views.dinner_detail, name='dinner_detail'),
    path('dinners/<int:dinner_id>/combined/', views.dinner_combined, name='dinner_combined'),
    path('dinners/add_to_shop/', views.add_dinner_to_shop, name='add_dinner_to_shop'),
]