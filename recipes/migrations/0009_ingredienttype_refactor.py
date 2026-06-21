from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_ingredient_types(apps, schema_editor):
    """
    For every existing Ingredient, create a matching IngredientType
    (using the ingredient's name and tagg), then link back.
    Deduplicates by name — same name = same IngredientType.
    """
    Ingredient = apps.get_model('recipes', 'Ingredient')
    IngredientType = apps.get_model('recipes', 'IngredientType')

    name_to_type = {}
    for ing in Ingredient.objects.select_related('tagg').all():
        key = ing.name.strip().lower()
        if key not in name_to_type:
            itype = IngredientType.objects.create(
                name=ing.name.strip(),
                tagg=ing.tagg,
            )
            name_to_type[key] = itype
        ing.ingredient_type = name_to_type[key]
        ing.save()


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0008_info_related_recipes'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Create the IngredientType catalog table
        migrations.CreateModel(
            name='IngredientType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
                ('shelf_life_days', models.IntegerField(
                    blank=True, null=True,
                    help_text='Expected shelf life in days (used to warn when pantry items get old)'
                )),
                ('tagg', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='recipes.Tagg',
                )),
            ],
            options={'ordering': ['name']},
        ),

        # 2. Add nullable ingredient_type FK to Ingredient
        migrations.AddField(
            model_name='ingredient',
            name='ingredient_type',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='recipes.IngredientType',
            ),
        ),

        # 3. Data migration: populate IngredientType from existing Ingredient rows
        migrations.RunPython(create_ingredient_types, migrations.RunPython.noop),

        # 4. Remove the old name and tagg fields from Ingredient
        migrations.RemoveField(model_name='ingredient', name='name'),
        migrations.RemoveField(model_name='ingredient', name='tagg'),

        # 5. Update PantryItem: add ingredient_type FK, remove old name/tagg fields
        migrations.AddField(
            model_name='pantryitem',
            name='ingredient_type',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='recipes.IngredientType',
            ),
        ),
        migrations.RemoveField(model_name='pantryitem', name='name'),
        migrations.RemoveField(model_name='pantryitem', name='tagg'),
    ]
