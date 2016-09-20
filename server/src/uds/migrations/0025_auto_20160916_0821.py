# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-16 08:21
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('uds', '0024_transport_allowed_oss'),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.CharField(default=None, max_length=50, null=True, unique=True)),
                ('name', models.CharField(db_index=True, max_length=128)),
                ('comments', models.CharField(max_length=256)),
            ],
            options={
                'db_table': 'uds_accounts',
            },
        ),
        migrations.CreateModel(
            name='AccountUsage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.CharField(default=None, max_length=50, null=True, unique=True)),
                ('user_name', models.CharField(db_index=True, default='', max_length=128)),
                ('user_uuid', models.CharField(db_index=True, default='', max_length=50)),
                ('pool_name', models.CharField(db_index=True, default='', max_length=128)),
                ('pool_uuid', models.CharField(db_index=True, default='', max_length=50)),
                ('start', models.DateTimeField(default=datetime.datetime(1972, 7, 1, 0, 0))),
                ('end', models.DateTimeField(default=datetime.datetime(1972, 7, 1, 0, 0))),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usages', to='uds.Account')),
            ],
            options={
                'db_table': 'uds_acc_usage',
            },
        ),
        migrations.AddField(
            model_name='deployedservice',
            name='account',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='servicesPools', to='uds.Account'),
        ),
    ]