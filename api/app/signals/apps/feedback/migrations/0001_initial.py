# Generated by Django 2.1.7 on 2019-03-26 10:15

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('signals', '0041_auto_20190325_1520'),
    ]

    operations = [
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('submitted_at', models.DateTimeField(editable=False, null=True)),
                ('is_satisfied', models.BooleanField(null=True)),
                ('allows_contact', models.BooleanField(default=False)),
                ('text', models.TextField(blank=True, max_length=1000, null=True)),
                ('text_extra', models.TextField(blank=True, max_length=1000, null=True)),
                ('_signal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feedback', to='signals.Signal')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StandardAnswer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_visible', models.BooleanField(default=True)),
                ('is_satisfied', models.BooleanField(default=True)),
                ('text', models.TextField(max_length=1000)),
            ],
        ),
    ]
