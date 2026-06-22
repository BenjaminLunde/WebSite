import datetime

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.forms import ModelForm
# Create your models here.


class RecipeTag(models.Model):
    """Tags for recipes, e.g. Vegetarian, Beef, Dinner, Snack, Main course."""
    name = models.CharField(max_length=80)

    def __str__(self):
        return self.name


class Info(models.Model):
    title = models.CharField(max_length=200, default="Empty")
    intro = models.CharField(max_length=4000, default="Needs no intro")
    difficulty = models.IntegerField(default=1)
    photo = models.ImageField(upload_to='images/', null=True, blank=True)
    pub_date = models.DateTimeField('date published')
    time = models.CharField(max_length=200, default="30 min")
    servings = models.IntegerField(default=6)
    recipe_tags = models.ManyToManyField(RecipeTag, blank=True)

    # Cook log — updated each time you finish cooking this recipe
    last_cooked = models.DateField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True, help_text="Your score 1–10")
    revision_notes = models.TextField(blank=True, help_text="Notes to improve it next time")

    # Drafts are only visible to staff (used by the recipe importer)
    is_draft = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    def was_published_recently(self):
        return self.pub_date >= timezone.now() - datetime.timedelta(days=1)


class Dinner(models.Model):
    """A curated dinner combining several recipes (main, side, sauce, etc.)."""
    title = models.CharField(max_length=200)
    description = models.CharField(max_length=2000, blank=True, default='')
    photo = models.ImageField(upload_to='images/', null=True, blank=True)
    pub_date = models.DateTimeField('date published')

    def __str__(self):
        return self.title


class DinnerComponent(models.Model):
    """One recipe that is part of a Dinner, with a free-text role label."""
    dinner = models.ForeignKey(Dinner, on_delete=models.CASCADE, related_name='components')
    recipe = models.ForeignKey('Info', on_delete=models.CASCADE)
    role = models.CharField(
        max_length=100, default='Main',
        help_text='Free text label, e.g. Main, Side, Sauce, Bread'
    )
    order = models.IntegerField(default=0, help_text='Lower number = shown first')
    default_selected = models.BooleanField(
        default=True,
        help_text='Pre-check this component on the dinner page'
    )

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.dinner.title}: [{self.role}] {self.recipe.title}"


class Tagg(models.Model):
    """Category for ingredients, e.g. Dairy, Meat, Vegetables."""
    name = models.CharField(max_length=80)

    def __str__(self):
        return self.name


class IngredientType(models.Model):
    """Central ingredient catalog. Shared by recipes, shopping list, and pantry."""
    name = models.CharField(max_length=200, unique=True)
    tagg = models.ForeignKey(Tagg, on_delete=models.SET_NULL, null=True, blank=True)
    shelf_life_days = models.IntegerField(
        null=True, blank=True,
        help_text="Expected shelf life in days (used to warn when pantry items get old)"
    )
    is_staple = models.BooleanField(
        default=False,
        help_text="Always available (water, salt, etc.) — unchecked by default on all recipe pages"
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """A specific ingredient in a recipe, with its quantity."""
    info = models.ForeignKey(Info, on_delete=models.CASCADE, null=True)
    ingredient_type = models.ForeignKey(IngredientType, on_delete=models.SET_NULL, null=True)
    measurment = models.CharField(max_length=200)

    @property
    def name(self):
        return self.ingredient_type.name if self.ingredient_type else ''

    @property
    def tagg(self):
        return self.ingredient_type.tagg if self.ingredient_type else None

    def __str__(self):
        return self.name


class IngredientForm(ModelForm):
    class Meta:
        model = Ingredient
        fields = ['ingredient_type', 'measurment']


class Instruction(models.Model):
    info = models.ForeignKey(Info, on_delete=models.CASCADE)
    text = models.CharField(max_length=2000)

    def __str__(self):
        return self.text


class IngredientToShop(models.Model):
    shopper = models.ForeignKey(User, on_delete=models.CASCADE)
    ingredient_type = models.ForeignKey(
        IngredientType, on_delete=models.CASCADE, null=True, blank=True
    )
    amount = models.CharField(max_length=200, default='')

    @property
    def name(self):
        return self.ingredient_type.name if self.ingredient_type else ''

    @property
    def tagg(self):
        return self.ingredient_type.tagg if self.ingredient_type else None

    def __str__(self):
        return self.name


class PantryItem(models.Model):
    """An ingredient the user currently has at home."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ingredient_type = models.ForeignKey(IngredientType, on_delete=models.SET_NULL, null=True)
    amount = models.CharField(max_length=200)
    added_date = models.DateTimeField(auto_now_add=True)

    @property
    def name(self):
        return self.ingredient_type.name if self.ingredient_type else ''

    @property
    def tagg(self):
        return self.ingredient_type.tagg if self.ingredient_type else None

    def days_old(self):
        return (timezone.now() - self.added_date).days

    def urgency(self):
        """Returns 'expired', 'warning', 'ok', or '' (no shelf life configured)."""
        if not self.ingredient_type or not self.ingredient_type.shelf_life_days:
            return ''
        days = self.days_old()
        shelf = self.ingredient_type.shelf_life_days
        if days >= shelf:
            return 'expired'
        elif days >= shelf * 0.75:
            return 'warning'
        return 'ok'

    def __str__(self):
        return self.name


class RecipeSource(models.Model):
    """
    Trusted cooking websites used by the recipe importer.
    Add these via the Django admin — the import page will list them
    and use their search patterns to find recipes.
    """
    name = models.CharField(max_length=100, help_text="Friendly name, e.g. 'AllRecipes'")
    base_url = models.URLField(help_text="e.g. https://www.allrecipes.com")
    search_url_pattern = models.CharField(
        max_length=500, blank=True,
        help_text="Search URL with {query} placeholder, e.g. https://www.allrecipes.com/search?q={query}"
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


User._meta.get_field('email').blank = False
