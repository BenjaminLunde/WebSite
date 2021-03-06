# Generated by Django 3.0.7 on 2021-01-01 22:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Info',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default='Empty', max_length=200)),
                ('intro', models.CharField(default='Needs no intro', max_length=400)),
                ('difficulty', models.IntegerField(default=1)),
                ('photo', models.ImageField(storage='/recpies/', upload_to='')),
                ('pub_date', models.DateTimeField(verbose_name='date published')),
                ('instruction', models.CharField(default='There are no instructions', max_length=4000)),
            ],
        ),
        migrations.CreateModel(
            name='Ingredient',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('count', models.IntegerField(default=1)),
                ('measurment', models.IntegerField(default=1)),
                ('info', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='recipes.Info')),
            ],
        ),
    ]
