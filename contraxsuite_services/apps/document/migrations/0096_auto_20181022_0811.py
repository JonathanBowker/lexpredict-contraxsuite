# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2018-10-22 08:11
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('document', '0095_auto_20181019_2329'),
    ]

    operations = [
        migrations.RenameField(
            model_name='classifiermodel',
            old_name='accuracy',
            new_name='accuracy_out_of_sample',
        ),
        migrations.RenameField(
            model_name='classifiermodel',
            old_name='test_documents_number',
            new_name='test_documents_number_out_of_sample',
        ),
        migrations.RenameField(
            model_name='classifiermodel',
            old_name='test_text_units_number',
            new_name='test_text_units_number_out_of_sample',
        ),
    ]
