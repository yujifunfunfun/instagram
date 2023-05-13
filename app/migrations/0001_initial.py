# Generated by Django 3.1.3 on 2023-04-27 04:17

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Insight',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('follower', models.IntegerField(verbose_name='フォロワー')),
                ('follows', models.IntegerField(verbose_name='フォロー')),
                ('label', models.CharField(max_length=100, verbose_name='作成日')),
            ],
        ),
    ]