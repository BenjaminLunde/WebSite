from django.contrib import admin
from recipes.models import (
    Ingredient, Instruction, Tagg, RecipeTag, PantryItem,
    IngredientType, Dinner, DinnerComponent, RecipeSource,
)
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
    filter_horizontal = ('recipe_tags',)


@admin.register(IngredientType)
class IngredientTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'tagg', 'shelf_life_days', 'is_staple')
    list_filter = ('tagg', 'is_staple')
    search_fields = ('name',)
    ordering = ('name',)


class DinnerComponentInline(admin.TabularInline):
    model = DinnerComponent
    fields = ('recipe', 'role', 'order', 'default_selected')
    extra = 1


@admin.register(Dinner)
class DinnerAdmin(admin.ModelAdmin):
    inlines = (DinnerComponentInline,)
    list_display = ('title', 'pub_date')


admin.site.register(Info, InfoAdmin)
admin.site.register(Tagg)
admin.site.register(RecipeTag)
admin.site.register(PantryItem)


@admin.register(RecipeSource)
class RecipeSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_url', 'is_active')
    list_filter = ('is_active',)
    help_texts = {
        'search_url_pattern': (
            'Use {query} as a placeholder for the search term. '
            'Example: https://www.allrecipes.com/search?q={query}'
        )
    }
