import datetime

from django.db import models
from django.utils import timezone

# Create your models here.


class Info(models.Model):
    instructions = models.CharField(max_length=200)
    title = models.CharField(max_length=200, default= "Empty")
    pub_date = models.DateTimeField('date published')

    def __str__(self):
        return self.title

    def was_published_recently(self):
        return self.pub_date >= timezone.now() - datetime.timedelta(days=1)


class Ingredient(models.Model):
    info = models.ForeignKey(Info, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    count = models.IntegerField(default=1)

    def __str__(self):
        return self.name