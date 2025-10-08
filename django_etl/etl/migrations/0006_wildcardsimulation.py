# Generated manually for WildcardSimulation model

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('etl', '0005_sofasportplayerattributes'),
    ]

    operations = [
        migrations.CreateModel(
            name='WildcardSimulation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.CharField(db_index=True, help_text='Unique shareable code (e.g., WC-ABC123)', max_length=10, unique=True)),
                ('squad_data', models.JSONField(default=dict, help_text='Player selections, formation, captain choices')),
                ('total_cost', models.DecimalField(decimal_places=1, default=Decimal('0.0'), help_text='Total squad cost in millions', max_digits=5)),
                ('predicted_points', models.IntegerField(default=0, help_text='Predicted total points for next gameweek')),
                ('gameweek', models.IntegerField(blank=True, help_text='Target gameweek for this wildcard', null=True)),
                ('team_name', models.CharField(blank=True, help_text='Optional user-provided team name', max_length=100)),
                ('is_saved', models.BooleanField(default=False, help_text="True if user clicked 'Save & Share', False if just drafting")),
                ('view_count', models.IntegerField(default=1, help_text='Number of times this team has been viewed')),
            ],
            options={
                'db_table': 'wildcard_simulations',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='wildcardsimulation',
            index=models.Index(fields=['code'], name='wildcard_si_code_idx'),
        ),
        migrations.AddIndex(
            model_name='wildcardsimulation',
            index=models.Index(fields=['created_at'], name='wildcard_si_created_idx'),
        ),
        migrations.AddIndex(
            model_name='wildcardsimulation',
            index=models.Index(fields=['is_saved'], name='wildcard_si_is_save_idx'),
        ),
    ]
