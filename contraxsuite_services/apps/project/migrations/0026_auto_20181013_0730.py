# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-10-13 07:30
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0025_auto_20181010_1739'),
    ]

    operations = [
        migrations.AlterField(
            model_name='uploadsession',
            name='project',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='project.Project'),
        ),
    ]
