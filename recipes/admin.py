from django.contrib import admin
from recipes.models import Ingredient, Instruction, Tagg, RecipeTag, PantryItem
from django.contrib.auth.models import User

from .models import Info

# Register your models here.

class IngredientAdminInline(admin.TabularInline):
    model = Ingredient

class InstructionAdminInline(admin.TabularInline):
    model = Instruction


class InfoAdmin(admin.ModelAdmin):
    inlines = (IngredientAdminInline, InstructionAdminInline, )
    filter_horizontal = ('recipe_tags', 'related_recipes',)

admin.site.register(Info, InfoAdmin)
admin.site.register(Tagg)
admin.site.register(RecipeTag)
admin.site.register(PantryItem)