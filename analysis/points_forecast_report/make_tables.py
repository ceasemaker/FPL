"""Turn sensitivity.json and usage_eval.json into LaTeX tables for the report.

    python analysis/points_forecast_report/make_tables.py

Writes sensitivity_table.tex and usage_table.tex next to this file; the
report \\input{}s them, so every number in those tables comes from a run.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def signed(value: float, digits: int = 2) -> str:
    return f"{'+' if value > 0 else '$-$' if value < 0 else ''}{abs(value):.{digits}f}"


def interval(entry: dict, digits: int = 2) -> str:
    return f"{signed(entry['mean'], digits)} [{signed(entry['low'], digits)}, {signed(entry['high'], digits)}]"


def sensitivity() -> None:
    data = json.loads((HERE / "sensitivity.json").read_text())
    lines = [
        r"\begin{tabular}{lccccc}",
        r"\toprule",
        r" & MAE & Corr. & Captain & vs top-100 & vs premium \\",
        r"\midrule",
    ]
    for name, row in data.items():
        label = "Reference model" if name == "baseline" else name[0].upper() + name[1:]
        lines.append(
            f"{label} & {row['mae']:.3f} & {row['corr']:.3f} & {row['captain']:.2f} & "
            f"{signed(row['versus']['elite']['mean'])} & {signed(row['versus']['premium']['mean'])} \\\\"
        )
        if name == "baseline" or name == "without minutes and starts":
            lines.append(r"\midrule")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (HERE / "sensitivity_table.tex").write_text("\n".join(lines) + "\n")


def usage() -> None:
    data = json.loads((HERE / "usage_eval.json").read_text())
    base, plus, paired = data["base"], data["with_usage"], data["paired"]
    lines = [
        r"\begin{tabular}{lccc}",
        r"\toprule",
        r" & Without usage & With usage & Difference [95\% interval] \\",
        r"\midrule",
        f"Mean absolute error & {base['mae']:.3f} & {plus['mae']:.3f} & {interval(paired['mae_reduction'], 3)}$^a$ \\\\",
        f"Correlation & {base['corr']:.3f} & {plus['corr']:.3f} & \\\\",
        f"Captain points per week & {base['captain']:.2f} & {plus['captain']:.2f} & {interval(paired['captain_points'])} \\\\",
        f"Lineup points per week & {base['lineup']:.2f} & {plus['lineup']:.2f} & {interval(paired['lineup_points'])} \\\\",
        f"MAE, players who changed club & & & {interval(paired['mae_reduction_movers'], 3)}$^a$ \\\\",
        r"\bottomrule",
        r"\end{tabular}",
    ]
    (HERE / "usage_table.tex").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    if (HERE / "sensitivity.json").exists():
        sensitivity()
    if (HERE / "usage_eval.json").exists():
        usage()
