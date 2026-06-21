from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0011_dinner_dinnercomponent'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='info',
            name='related_recipes',
        ),
    ]
