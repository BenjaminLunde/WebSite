# Generated by Django 3.0.7 on 2021-01-04 08:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0004_auto_20210104_0904'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ingredient',
            name='info',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='recipes.Info'),
        ),
    ]
