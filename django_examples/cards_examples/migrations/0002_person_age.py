# Generated by Django 3.2.7 on 2022-11-28 14:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cards_examples', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='age',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]