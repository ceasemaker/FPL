# Generated migration for performance indexes
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('etl', '0002_alter_setpiecenote_note'),
    ]

    operations = [
        # Add indexes to Athlete model for faster queries
        migrations.AddIndex(
            model_name='athlete',
            index=models.Index(fields=['-total_points'], name='athletes_total_p_idx'),
        ),
        migrations.AddIndex(
            model_name='athlete',
            index=models.Index(fields=['element_type'], name='athletes_elem_ty_idx'),
        ),
        migrations.AddIndex(
            model_name='athlete',
            index=models.Index(fields=['element_type', '-total_points'], name='athletes_elem_pt_idx'),
        ),
        # Add indexes to Fixture model for faster FDR calculation
        migrations.AddIndex(
            model_name='fixture',
            index=models.Index(fields=['event'], name='fixtures_event_idx'),
        ),
        migrations.AddIndex(
            model_name='fixture',
            index=models.Index(fields=['team_h', 'event'], name='fixtures_team_h_idx'),
        ),
        migrations.AddIndex(
            model_name='fixture',
            index=models.Index(fields=['team_a', 'event'], name='fixtures_team_a_idx'),
        ),
    ]
