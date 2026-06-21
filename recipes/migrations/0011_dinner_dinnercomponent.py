from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0010_info_photo_optional'),
    ]

    operations = [
        migrations.CreateModel(
            name='Dinner',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.CharField(blank=True, default='', max_length=2000)),
                ('photo', models.ImageField(blank=True, null=True, upload_to='images/')),
                ('pub_date', models.DateTimeField(verbose_name='date published')),
            ],
        ),
        migrations.CreateModel(
            name='DinnerComponent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(default='Main', max_length=100)),
                ('order', models.IntegerField(default=0)),
                ('default_selected', models.BooleanField(default=True)),
                ('dinner', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='components',
                    to='recipes.Dinner',
                )),
                ('recipe', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='recipes.Info',
                )),
            ],
            options={
                'ordering': ['order', 'id'],
            },
        ),
    ]
