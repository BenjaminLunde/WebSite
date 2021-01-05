"""mysite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, reverse_lazy, path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    #url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    path('', include('homepage.urls')),
    path('recipes/', include('recipes.urls')),
    path('resume/', include('resume.urls')),
    path('contact/', include('contact.urls')),
    path('admin/', admin.site.urls),
        path('password_reset/',  auth_views.PasswordResetView.as_view(
    template_name='recipes/password_reset.html',
    email_template_name='recipes/password_reset_email.html',
    subject_template_name='recipes/password_reset_subject.txt',
    success_url=reverse_lazy('recipes:password_reset_done')), 
    name='password_reset'),

    path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(
    template_name='recipes/password_reset_done.html'), 
    name='password_reset_done'),

    path('password_reset_<uidb64>_<token>/', auth_views.PasswordResetConfirmView.as_view(
    template_name='recipes/password_reset_confirm.html',
    success_url=reverse_lazy('recipes:password_reset_complete')), 
    name='password_reset_confirm'),

    path('password_reset_complete/', auth_views.PasswordResetCompleteView.as_view(
    template_name='recipes/password_reset_complete.html'), 
    name='password_reset_complete'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

