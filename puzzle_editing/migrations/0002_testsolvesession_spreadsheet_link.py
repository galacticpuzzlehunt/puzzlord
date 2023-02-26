# Generated by Django 4.0.3 on 2023-02-26 02:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('puzzle_editing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='testsolvesession',
            name='spreadsheet_link',
            field=models.CharField(blank=True, help_text='Link to the testsolve spreadsheet.', max_length=200),
        ),
    ]