"""
Migration 0015 — Redesign IngredientToShop.

Old schema:  ingredient  FK → Ingredient  (borrows quantity from the recipe row)
New schema:  ingredient_type FK → IngredientType  +  amount CharField

Shopping-list data is transient (cleared after every shopping trip), so we
just delete any existing rows rather than attempting a lossy migration.
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0014_recipesource_info_is_draft_info_last_cooked_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Wipe existing rows so we can safely swap the FK column.
        migrations.RunSQL(
            sql='DELETE FROM recipes_ingredienttoshop;',
            reverse_sql=migrations.RunSQL.noop,
        ),

        # 2. Drop the old ingredient FK.
        migrations.RemoveField(
            model_name='ingredienttoshop',
            name='ingredient',
        ),

        # 3. Add ingredient_type FK.
        migrations.AddField(
            model_name='ingredienttoshop',
            name='ingredient_type',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='recipes.ingredienttype',
            ),
        ),

        # 4. Add amount field.
        migrations.AddField(
            model_name='ingredienttoshop',
            name='amount',
            field=models.CharField(default='', max_length=200),
        ),
    ]
