import datetime

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.forms import ModelForm
# Create your models here.


class Info(models.Model):
    title = models.CharField(max_length=200, default= "Empty")
    intro = models.CharField(max_length=4000, default= "Needs no intro")
    difficulty = models.IntegerField(default=1)
    photo = models.ImageField(upload_to='images/')
    pub_date = models.DateTimeField('date published')
    time = models.CharField(max_length=200, default= "30 min")
    servings = models.IntegerField(default=6)

    def __str__(self):
        return self.title

    def was_published_recently(self):
        return self.pub_date >= timezone.now() - datetime.timedelta(days=1)

class Tagg(models.Model):
    name = models.CharField(max_length=80)

    def __str__(self):
        return self.name

class Ingredient(models.Model):
    info = models.ForeignKey(Info, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=200)
    measurment = models.CharField(max_length=200)
    tagg = models.ForeignKey(Tagg, on_delete=models.SET_NULL, null=True)


    def __str__(self):
        return self.name

class IngredientForm(ModelForm):
    class Meta:
        model = Ingredient
        fields = ['name', 'measurment', "tagg"]

class Instruction(models.Model):
    info = models.ForeignKey(Info, on_delete=models.CASCADE)
    text = models.CharField(max_length=2000)

    def __str__(self):
        return self.text

class IngredientToShop(models.Model):
    shopper = models.ForeignKey(User, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)

    def __str__(self):
        return self.ingredient.name


User._meta.get_field('email').blank = False

