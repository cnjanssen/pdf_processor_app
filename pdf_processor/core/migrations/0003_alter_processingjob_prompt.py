# Generated by Django 5.1.2 on 2024-10-30 01:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_processingjob_columns"),
    ]

    operations = [
        migrations.AlterField(
            model_name="processingjob",
            name="prompt",
            field=models.TextField(blank=True),
        ),
    ]