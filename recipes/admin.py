from django.contrib import admin
from recipes.models import Ingredient, Instruction, Tagg, RecipeTag, PantryItem, IngredientType
from django.contrib.auth.models import User

from .models import Info

# Register your models here.


class IngredientAdminInline(admin.TabularInline):
    model = Ingredient
    fields = ('ingredient_type', 'measurment')
    # Django automatically adds a + popup button next to ingredient_type
    # so new ingredient types can be created without leaving the recipe page


class InstructionAdminInline(admin.TabularInline):
    model = Instruction


class InfoAdmin(admin.ModelAdmin):
    inlines = (IngredientAdminInline, InstructionAdminInline,)
    filter_horizontal = ('recipe_tags', 'related_recipes',)


@admin.register(IngredientType)
class IngredientTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'tagg', 'shelf_life_days')
    list_filter = ('tagg',)
    search_fields = ('name',)
    ordering = ('name',)


admin.site.register(Info, InfoAdmin)
admin.site.register(Tagg)
admin.site.register(RecipeTag)
admin.site.register(PantryItem)
