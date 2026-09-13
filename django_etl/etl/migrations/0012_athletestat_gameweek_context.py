from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('etl', '0011_athleteprediction_assist_prob_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='athletestat',
            name='selected',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='athletestat',
            name='transfers_in',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='athletestat',
            name='transfers_out',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='athletestat',
            name='value',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
