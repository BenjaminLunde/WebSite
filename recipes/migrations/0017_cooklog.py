import django.db.models.deletion
from django.db import migrations, models


def seed_cook_logs(apps, schema_editor):
    """Create one CookLog per recipe that already has last_cooked set."""
    Info = apps.get_model('recipes', 'Info')
    CookLog = apps.get_model('recipes', 'CookLog')
    for recipe in Info.objects.filter(last_cooked__isnull=False):
        CookLog.objects.create(
            info=recipe,
            date=recipe.last_cooked,
            score=recipe.score,
            notes=recipe.revision_notes or '',
        )


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0016_ingredienttype_is_always_available'),
    ]

    operations = [
        migrations.CreateModel(
            name='CookLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('score', models.IntegerField(blank=True, help_text='Score 1–10', null=True)),
                ('notes', models.TextField(blank=True, help_text='Notes from this cook')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('info', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cook_logs',
                    to='recipes.info',
                )),
            ],
            options={
                'ordering': ['-date', '-created_at'],
            },
        ),
        migrations.RunPython(seed_cook_logs, migrations.RunPython.noop),
    ]
