from __future__ import annotations

from datetime import date

import django
from django.test import SimpleTestCase

django.setup()

from ..services.football_data import csv_url, parse_premier_league_csv, season_code


class FootballDataTests(SimpleTestCase):
    def test_season_code_rolls_over_in_july(self) -> None:
        self.assertEqual(season_code(date(2026, 8, 28)), "2627")
        self.assertEqual(season_code(date(2027, 1, 10)), "2627")

    def test_current_csv_url(self) -> None:
        self.assertEqual(
            csv_url("2627"),
            "https://www.football-data.co.uk/mmz4281/2627/E0.csv",
        )

    def test_parser_keeps_historical_market_fields(self) -> None:
        content = (
            "Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,AvgH,AvgD,AvgA,"
            "Avg>2.5,Avg<2.5,AvgCH,AvgCD,AvgCA,AvgC>2.5,AvgC<2.5\n"
            "E0,21/08/2026,20:00,Arsenal,Coventry,3,0,H,1.19,6.77,14.19,"
            "1.55,2.38,1.18,6.80,15.00,1.53,2.42\n"
        ).encode()

        rows = parse_premier_league_csv(content)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["HomeTeam"], "Arsenal")
        self.assertEqual(rows[0]["AvgH"], "1.19")
        self.assertEqual(rows[0]["AvgC>2.5"], "1.53")
