"""Management command to train ML prediction models and populate predictions."""
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Max

from etl.models import Athlete, AthletePrediction, AthleteStat
from etl.services.fixture_market import (
    build_market_lookup,
    calibrate_points,
    calibrate_probability,
)
from etl.ml.model import train_and_save_models, predict_points, predict_probability

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Train ML prediction models and populate next gameweek predictions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-training",
            action="store_true",
            help="Skip model training, only populate predictions"
        )
        parser.add_argument(
            "--gameweek",
            type=int,
            help="Specific gameweek to predict for (default: current_gw + 1)"
        )

    def handle(self, *args, **options):
        skip_training = options.get("skip_training", False)
        gameweek = options.get("gameweek")

        try:
            # Train models if not skipping
            if not skip_training:
                self.stdout.write("Training ML models...")
                train_and_save_models()
                self.stdout.write(self.style.SUCCESS("✓ Models trained successfully"))

            # Determine gameweek to predict for
            if not gameweek:
                max_gw = AthleteStat.objects.aggregate(max_gw=Max("game_week"))["max_gw"] or 0
                gameweek = max_gw + 1

            self.stdout.write(f"Populating predictions for GW{gameweek}...")

            # Get all athletes
            athletes = Athlete.objects.select_related("team").all()
            market_lookup = build_market_lookup(gameweek)
            created_count = 0
            updated_count = 0
            market_adjusted_count = 0

            for athlete in athletes:
                try:
                    # Predict points
                    predicted_points = predict_points(athlete.id, gameweek)
                    market_adjustment = market_lookup.get(
                        (athlete.team_id, athlete.element_type)
                    )
                    predicted_points = calibrate_points(
                        predicted_points,
                        market_adjustment,
                    )
                    if market_adjustment is not None:
                        market_adjusted_count += 1

                    # Get probability predictions based on position
                    clean_sheet_prob = None
                    goal_prob = None
                    assist_prob = None
                    bonus_prob = None

                    if athlete.element_type in (1, 2):  # GK/DEF
                        clean_sheet_prob = predict_probability(athlete.id, gameweek, "clean_sheet")
                        if market_adjustment is not None:
                            clean_sheet_prob = calibrate_probability(
                                clean_sheet_prob,
                                market_adjustment.clean_sheet_prob,
                            )

                    if athlete.element_type in (3, 4):  # MID/FWD
                        goal_prob = predict_probability(athlete.id, gameweek, "goal")
                        assist_prob = predict_probability(athlete.id, gameweek, "assist")

                        if market_adjustment is not None:
                            goal_prob = calibrate_probability(
                                goal_prob,
                                min(1.0, goal_prob * market_adjustment.multiplier),
                            )
                            assist_prob = calibrate_probability(
                                assist_prob,
                                min(1.0, assist_prob * market_adjustment.multiplier),
                            )

                    bonus_prob = predict_probability(athlete.id, gameweek, "bonus")
                    if market_adjustment is not None:
                        bonus_prob = calibrate_probability(
                            bonus_prob,
                            min(1.0, bonus_prob * market_adjustment.multiplier),
                        )

                    # Create or update prediction
                    prediction, created = AthletePrediction.objects.update_or_create(
                        athlete_id=athlete.id,
                        game_week=gameweek,
                        defaults={
                            "predicted_points": predicted_points,
                            "clean_sheet_prob": clean_sheet_prob,
                            "goal_prob": goal_prob,
                            "assist_prob": assist_prob,
                            "bonus_prob": bonus_prob,
                        }
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                except Exception as e:
                    logger.error(f"Error predicting for athlete {athlete.id}: {e}")

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Created {created_count}, updated {updated_count} predictions for GW{gameweek}; "
                    f"market-calibrated {market_adjusted_count}"
                )
            )

        except Exception as e:
            logger.error(f"Error in training/prediction: {e}", exc_info=True)
            self.stderr.write(self.style.ERROR(f"Failed: {e}"))
            raise
