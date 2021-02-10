from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

def index(request):
    return render(request, 'homepage/index.html', {})

def resume(request):
    return render(request, 'homepage/resume.html', {})

def contact(request):
    return render(request, 'homepage/contact.html', {})