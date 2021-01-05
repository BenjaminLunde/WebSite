from django.contrib import admin
from recipes.models import Ingredient, Instruction, Tagg
from django.contrib.auth.models import User

from .models import Info

# Register your models here.

# admin.site.register(Info)

class IngredientAdminInline(admin.TabularInline):
    model = Ingredient

class InstructionAdminInline(admin.TabularInline):
    model = Instruction


class InfoAdmin(admin.ModelAdmin):
    inlines = (IngredientAdminInline, InstructionAdminInline, )
admin.site.register(Info, InfoAdmin)
admin.site.register(Tagg)