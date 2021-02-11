from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from . import views

app_name = 'homepage'
urlpatterns = [
    path('', views.index, name='index'),
    path('contact/', views.contact, name="contact"),
    path('resume/', views.resume, name="resume"),
]  + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)