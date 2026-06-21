from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0009_ingredienttype_refactor'),
    ]

    operations = [
        migrations.AlterField(
            model_name='info',
            name='photo',
            field=models.ImageField(upload_to='images/', null=True, blank=True),
        ),
    ]
