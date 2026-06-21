from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_ingredient_types(apps, schema_editor):
    """
    For every existing Ingredient, create a matching IngredientType
    (using the ingredient's name and tagg_id), then link back.
    Deduplicates by lowercased name.
    Uses raw _id fields to avoid ORM complexity on historical models.
    """
    Ingredient = apps.get_model('recipes', 'Ingredient')
    IngredientType = apps.get_model('recipes', 'IngredientType')

    name_to_type_id = {}
    for ing in Ingredient.objects.all():
        # Safely get the name — CharField should never be None, but guard anyway
        raw_name = ing.name if ing.name else ''
        clean_name = raw_name.strip()
        key = clean_name.lower()

        # Give truly nameless ingredients a placeholder so they don't collide
        if not key:
            clean_name = f'Ingredient {ing.pk}'
            key = clean_name.lower()

        if key not in name_to_type_id:
            itype = IngredientType.objects.create(
                name=clean_name,
                tagg_id=ing.tagg_id,   # use the raw FK column — no extra query
            )
            name_to_type_id[key] = itype.pk

        # Set the FK by PK to avoid any ORM state issues
        Ingredient.objects.filter(pk=ing.pk).update(
            ingredient_type_id=name_to_type_id[key]
        )


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
