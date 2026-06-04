#!/usr/bin/env python3
"""Apply GNOME light/dark theme based on sunrise and sunset."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


SCHEMA = "org.gnome.desktop.interface"
COLOR_SCHEME_KEY = "color-scheme"
GTK_THEME_KEY = "gtk-theme"
ICON_THEME_KEY = "icon-theme"

LIGHT_COLOR_SCHEME = "prefer-light"
DARK_COLOR_SCHEME = "prefer-dark"
LIGHT_GTK_THEME = "Yaru"
DARK_GTK_THEME = "Yaru-dark"
LIGHT_ICON_THEME = "Yaru"
DARK_ICON_THEME = "Yaru-dark"

CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "auto-theme-switcher"
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "auto-theme-switcher"
CONFIG_FILE = CONFIG_DIR / "config.json"
SUN_CACHE_FILE = CACHE_DIR / "sun.json"
LOCATION_CACHE_FILE = CACHE_DIR / "location.json"
HTTP_HEADERS = {"User-Agent": "auto-theme-switcher/1.0"}


@dataclass(frozen=True)
class Location:
    lat: float
    lng: float


@dataclass(frozen=True)
class SunTimes:
    sunrise: dt.datetime
    sunset: dt.datetime


def parse_iso_datetime(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def theme_for_time(now: dt.datetime, sunrise: dt.datetime, sunset: dt.datetime) -> str:
    return "light" if sunrise <= now < sunset else "dark"


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_config(path: Path = CONFIG_FILE) -> dict:
    if not path.exists():
        return {}
    return read_json(path)


def config_location(config: dict) -> Location | None:
    location = config.get("location", {})
    lat = location.get("lat")
    lng = location.get("lng")
    if lat is None or lng is None:
        return None
    return Location(float(lat), float(lng))


def fetch_location() -> Location:
    with urllib.request.urlopen("https://ipwho.is/", timeout=10) as response:
        payload = json.load(response)

    if payload.get("success") is False:
        raise RuntimeError(payload.get("message", "location lookup failed"))

    return Location(float(payload["latitude"]), float(payload["longitude"]))


def cached_location(cache_file: Path = LOCATION_CACHE_FILE) -> Location | None:
    if not cache_file.exists():
        return None
    data = read_json(cache_file)
    return Location(float(data["lat"]), float(data["lng"]))


def get_location(config: dict, cache_file: Path = LOCATION_CACHE_FILE) -> Location:
    configured = config_location(config)
    if configured:
        return configured

    try:
        location = fetch_location()
    except Exception:
        cached = cached_location(cache_file)
        if cached:
            return cached
        raise

    write_json(cache_file, {"lat": location.lat, "lng": location.lng})
    return location


def fetch_sun_times(lat: float, lng: float, today: dt.date) -> SunTimes:
    query = urllib.parse.urlencode(
        {
            "lat": lat,
            "lng": lng,
            "date": today.isoformat(),
            "formatted": 0,
        }
    )
    url = f"https://api.sunrise-sunset.org/json?{query}"

    request = urllib.request.Request(url, headers=HTTP_HEADERS)
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.load(response)

    if payload.get("status") != "OK":
        raise RuntimeError(f"sunrise-sunset.org returned {payload.get('status', 'unknown error')}")

    results = payload["results"]
    return SunTimes(parse_iso_datetime(results["sunrise"]), parse_iso_datetime(results["sunset"]))


def load_cached_sun_times(
    lat: float,
    lng: float,
    today: dt.date,
    cache_file: Path = SUN_CACHE_FILE,
) -> SunTimes | None:
    if not cache_file.exists():
        return None

    data = read_json(cache_file)
    if data.get("date") != today.isoformat():
        return None
    if round(float(data.get("lat", 0)), 4) != round(lat, 4):
        return None
    if round(float(data.get("lng", 0)), 4) != round(lng, 4):
        return None

    return SunTimes(parse_iso_datetime(data["sunrise"]), parse_iso_datetime(data["sunset"]))


def save_sun_times(
    lat: float,
    lng: float,
    today: dt.date,
    sun_times: SunTimes,
    cache_file: Path = SUN_CACHE_FILE,
) -> None:
    write_json(
        cache_file,
        {
            "date": today.isoformat(),
            "lat": lat,
            "lng": lng,
            "sunrise": sun_times.sunrise.isoformat(),
            "sunset": sun_times.sunset.isoformat(),
        },
    )


def get_sun_times(
    lat: float,
    lng: float,
    today: dt.date,
    cache_file: Path = SUN_CACHE_FILE,
) -> SunTimes:
    try:
        sun_times = fetch_sun_times(lat, lng, today)
    except Exception:
        cached = load_cached_sun_times(lat, lng, today, cache_file)
        if cached:
            return cached
        raise

    save_sun_times(lat, lng, today, sun_times, cache_file)
    return sun_times


def command_output(args: list[str]) -> str:
    return subprocess.check_output(args, text=True).strip().strip("'")


def command_run(args: list[str]) -> str:
    subprocess.run(args, check=True)
    return ""


def desired_settings(theme: str, config: dict | None = None) -> dict[str, str]:
    config = config or {}
    themes = config.get("themes", {})
    if theme == "light":
        defaults = {
            COLOR_SCHEME_KEY: LIGHT_COLOR_SCHEME,
            GTK_THEME_KEY: LIGHT_GTK_THEME,
            ICON_THEME_KEY: LIGHT_ICON_THEME,
        }
    else:
        defaults = {
            COLOR_SCHEME_KEY: DARK_COLOR_SCHEME,
            GTK_THEME_KEY: DARK_GTK_THEME,
            ICON_THEME_KEY: DARK_ICON_THEME,
        }

    overrides = themes.get(theme, {})
    return {key: str(overrides.get(key, value)) for key, value in defaults.items()}


def apply_theme(
    theme: str,
    config: dict | None = None,
    runner: Callable[[list[str]], str] = command_output,
) -> bool:
    settings = desired_settings(theme, config)
    changed = False
    for key, value in settings.items():
        current_value = runner(["gsettings", "get", SCHEMA, key])
        if current_value != value:
            if runner is command_output:
                command_run(["gsettings", "set", SCHEMA, key, value])
            else:
                runner(["gsettings", "set", SCHEMA, key, value])
            changed = True

    return changed


def run(now: dt.datetime | None = None, config_file: Path = CONFIG_FILE) -> str:
    now = now or dt.datetime.now().astimezone()
    config = load_config(config_file)
    location = get_location(config)
    sun_times = get_sun_times(location.lat, location.lng, now.date())
    theme = theme_for_time(now, sun_times.sunrise, sun_times.sunset)
    changed = apply_theme(theme, config)
    return f"{theme} theme {'applied' if changed else 'already active'}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_FILE)
    parser.add_argument("--print-only", action="store_true", help="print the chosen theme without changing GNOME settings")
    args = parser.parse_args(argv)

    try:
        now = dt.datetime.now().astimezone()
        config = load_config(args.config)
        location = get_location(config)
        sun_times = get_sun_times(location.lat, location.lng, now.date())
        theme = theme_for_time(now, sun_times.sunrise, sun_times.sunset)
        if args.print_only:
            print(theme)
        else:
            changed = apply_theme(theme, config)
            print(f"{theme} theme {'applied' if changed else 'already active'}")
    except Exception as error:
        print(f"auto-theme-switcher: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
