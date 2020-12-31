from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.template import loader

from .models import Info


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
    return render(request, 'recipes/info.html', {'info':info})