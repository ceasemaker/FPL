from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from ..management.commands.train_prediction_model import availability_factor
from ..models import Athlete, AthletePrediction

COMMAND = "etl.management.commands.train_prediction_model"


class TrainPredictionModelCommandTests(TestCase):
    def test_skip_training_retrains_when_model_files_are_missing(self) -> None:
        # Missing before training, present after it.
        with patch(f"{COMMAND}.models_available", side_effect=[False, True]), patch(
            f"{COMMAND}.train_and_save_models"
        ) as train:
            call_command("train_prediction_model", "--skip-training", stdout=StringIO())

        train.assert_called_once()

    def test_skip_training_reuses_existing_models(self) -> None:
        with patch(f"{COMMAND}.models_available", return_value=True), patch(
            f"{COMMAND}.train_and_save_models"
        ) as train:
            call_command("train_prediction_model", "--skip-training", stdout=StringIO())

        train.assert_not_called()

    def test_refuses_to_write_predictions_without_a_model(self) -> None:
        with patch(f"{COMMAND}.models_available", return_value=False), patch(
            f"{COMMAND}.train_and_save_models"
        ), self.assertRaises(CommandError):
            call_command(
                "train_prediction_model",
                "--skip-training",
                stdout=StringIO(),
                stderr=StringIO(),
            )

        self.assertFalse(AthletePrediction.objects.exists())


class AvailabilityFactorTests(TestCase):
    def _athlete(self, **fields) -> Athlete:
        defaults = {"removed": False, "status": "a", "chance_of_playing_next_round": None}
        defaults.update(fields)
        return Athlete(**defaults)

    def test_fit_player_keeps_full_projection(self) -> None:
        self.assertEqual(availability_factor(self._athlete()), 1.0)

    def test_injured_suspended_and_removed_players_project_zero(self) -> None:
        for status in ("i", "s", "u", "n"):
            self.assertEqual(availability_factor(self._athlete(status=status)), 0.0)
        self.assertEqual(availability_factor(self._athlete(removed=True)), 0.0)

    def test_doubtful_player_scales_by_chance_of_playing(self) -> None:
        athlete = self._athlete(status="d", chance_of_playing_next_round=75)
        self.assertEqual(availability_factor(athlete), 0.75)
