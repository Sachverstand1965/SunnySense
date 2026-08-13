"""Transparent, dependency-free learning model."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, exp, radians, sin
from typing import Any

from .const import FACADES, FACADE_HALF_ANGLE, MODEL_NAMES


def circular_distance(a: float, b: float) -> float:
    """Return the shortest angular distance."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


def active_facade(azimuth: float) -> dict[str, Any] | None:
    """Select the nearest facade whose illumination sector contains azimuth."""
    candidates = [
        facade
        for facade in FACADES
        if circular_distance(azimuth, facade["bearing"]) <= FACADE_HALF_ANGLE
    ]
    return min(candidates, key=lambda f: circular_distance(azimuth, f["bearing"]), default=None)


def incidence_factor(azimuth: float, elevation: float, bearing: float, tilt: float) -> float:
    """Return cosine of incidence angle for a tilted surface.

    Tilt is measured from horizontal: 0° is flat, 90° is vertical.
    """
    elevation_rad = radians(elevation)
    tilt_rad = radians(tilt)
    azimuth_delta = radians(circular_distance(azimuth, bearing))
    return (
        sin(elevation_rad) * cos(tilt_rad)
        + cos(elevation_rad) * sin(tilt_rad) * cos(azimuth_delta)
    )


def cell_key(azimuth: float, elevation: float) -> str:
    """Quantize sun position; interpolation later uses neighbouring cells."""
    return f"{int(round(azimuth / 10.0) * 10) % 360}:{int(round(elevation / 5.0) * 5)}"


@dataclass(slots=True)
class Estimate:
    expected: float | None
    samples: int
    confidence: float


class SunnyModel:
    """Per-facade upper-envelope model with persistent serializable state."""

    def __init__(self, raw: dict[str, Any] | None = None) -> None:
        self.cells: dict[str, dict[str, dict[str, float | int]]] = {
            name: {} for name in MODEL_NAMES
        }
        if raw:
            for facade, cells in raw.get("cells", {}).items():
                if facade in self.cells and isinstance(cells, dict):
                    self.cells[facade] = cells
        self.thresholds: dict[str, dict[str, float]] = {
            name: {"on": 0.82, "off": 0.68} for name in MODEL_NAMES
        }
        if raw:
            for facade, values in raw.get("thresholds", {}).items():
                if facade in self.thresholds and isinstance(values, dict):
                    self.thresholds[facade] = {
                        "on": float(values.get("on", 0.82)),
                        "off": float(values.get("off", 0.68)),
                    }

    def estimate(self, facade: str, azimuth: float, elevation: float) -> Estimate:
        """Blend nearby learned reference cells by distance."""
        weighted = total_weight = 0.0
        samples = 0
        for key, cell in self.cells[facade].items():
            az, el = (float(part) for part in key.split(":"))
            distance = circular_distance(azimuth, az) / 10.0 + abs(elevation - el) / 5.0
            if distance > 2.5:
                continue
            count = int(cell["samples"])
            weight = exp(-distance) * min(1.0, count / 8.0)
            weighted += float(cell["reference"]) * weight
            total_weight += weight
            samples += count
        expected = weighted / total_weight if total_weight else None
        confidence = min(1.0, total_weight / 1.5)
        return Estimate(expected, samples, confidence)

    def learn(self, facade: str, azimuth: float, elevation: float, pv: float) -> None:
        """Track a robust upper envelope: fast upward, very slow downward."""
        key = cell_key(azimuth, elevation)
        cell = self.cells[facade].setdefault(key, {"reference": pv, "samples": 0})
        old = float(cell["reference"])
        alpha = 0.12 if pv >= old else 0.003
        cell["reference"] = round(old + alpha * (pv - old), 3)
        cell["samples"] = int(cell["samples"]) + 1

    def adapt_thresholds(self, facade: str, ratio: float, likely_clear: bool) -> None:
        """Slowly adapt hysteresis using only high-confidence proxy labels."""
        values = self.thresholds[facade]
        if likely_clear:
            target = min(0.90, max(0.74, ratio * 0.82))
            values["on"] += 0.01 * (target - values["on"])
        else:
            target = min(0.78, max(0.45, ratio + 0.05))
            values["off"] += 0.005 * (target - values["off"])
        values["on"] = min(0.92, max(0.72, values["on"]))
        values["off"] = min(values["on"] - 0.10, max(0.45, values["off"]))

    def as_dict(self) -> dict[str, Any]:
        return {"version": 1, "cells": self.cells, "thresholds": self.thresholds}


def learning_allowed(
    *, elevation: float, pv: float, lux: float | None, cloud: float | None,
    temperature: float | None,
) -> bool:
    """Use only likely clear, valid observations for the reference envelope."""
    if elevation < 10 or pv <= 0:
        return False
    signals = 0
    if lux is not None and lux >= 30_000:
        signals += 1
    if cloud is not None and cloud <= 30:
        signals += 1
    if temperature is not None and temperature >= -20:
        signals += 1
    return signals >= 2
