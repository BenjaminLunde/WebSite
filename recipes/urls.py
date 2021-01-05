from django.urls import path, include
from .views import SignUpView
from django.conf.urls import url


from . import views

app_name = 'recipes'
urlpatterns = [
    path('', views.index, name='index'),
    path('<int:info_id>/', views.get_one, name="get_one"),
    path('shopping/', views.shopping, name="shopping"),
    path('accounts/', include('django.contrib.auth.urls')),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('account/', views.account, name="account"),
    path('delete/<int:ingredientToShop_id>', views.delete_shop, name='delete'),
    path('delete_all/', views.delete_all, name='delete_all'),
    path('add_to_shop/', views.add_to_shop, name='add_to_shop')
]