from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0012_remove_related_recipes'),
    ]

    operations = [
        migrations.AddField(
            model_name='ingredienttype',
            name='is_staple',
            field=models.BooleanField(
                default=False,
                help_text='Always available (water, salt, etc.) — unchecked by default on all recipe pages',
            ),
        ),
    ]
