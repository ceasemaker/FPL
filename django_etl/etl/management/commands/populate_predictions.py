from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Disabled: random forecasts must never be written as model predictions"

    def handle(self, *args, **kwargs):
        raise CommandError(
            "Random prediction generation has been disabled because it produces "
            "untraceable forecasts. Use `python manage.py train_prediction_model` "
            "after validating the historical feature snapshots."
        )
