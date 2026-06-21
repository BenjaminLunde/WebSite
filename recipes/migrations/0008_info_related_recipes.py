from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0007_recipetag_pantryitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='info',
            name='related_recipes',
            field=models.ManyToManyField(blank=True, to='recipes.Info'),
        ),
    ]
