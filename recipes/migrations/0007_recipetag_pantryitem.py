from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0006_auto_20210104_2016'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Create the RecipeTag table
        migrations.CreateModel(
            name='RecipeTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80)),
            ],
        ),
        # 2. Add M2M from Info -> RecipeTag
        migrations.AddField(
            model_name='info',
            name='recipe_tags',
            field=models.ManyToManyField(blank=True, to='recipes.RecipeTag'),
        ),
        # 3. Create the PantryItem table
        migrations.CreateModel(
            name='PantryItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('amount', models.CharField(max_length=200)),
                ('added_date', models.DateTimeField(auto_now_add=True)),
                ('tagg', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='recipes.Tagg',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
    ]
