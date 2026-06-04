# Auto Theme Switcher for GNOME

Auto Theme Switcher switches GNOME between light and dark mode using your local sunrise and sunset times.

It is just a small Python script, not a background daemon. A `systemd --user` timer runs it every 10 minutes, and a GNOME autostart entry runs it once after graphical login.

## Requirements

- GNOME
- Python 3
- `gsettings`
- `systemd --user`
- Internet access at least once a day to refresh sunrise and sunset data

## Install

From the project directory, run:

```bash
./install.sh
````

This creates:

- `~/.config/systemd/user/auto-theme-switcher.service`
- `~/.config/systemd/user/auto-theme-switcher.timer`
- `~/.config/autostart/auto-theme-switcher.desktop`

To check that it is installed and running:

```bash
systemctl --user status auto-theme-switcher.timer
systemctl --user start auto-theme-switcher.service
journalctl --user -u auto-theme-switcher.service -n 50
```

To uninstall:

```bash
./uninstall.sh
```

## How it works

On each run, `auto_theme_switcher.py`:

1. Gets your latitude and longitude.
2. Fetches today's sunrise and sunset from `sunrise-sunset.org`.
3. Caches the result in `~/.cache/auto-theme-switcher/sun.json`.
4. Uses `prefer-light` between sunrise and sunset.
5. Uses `prefer-dark` outside daylight hours.
6. Changes the GTK and icon themes only when the current value is different.

By default, the script gets your location from `https://ipwho.is/` and caches the returned latitude and longitude. If that lookup fails, it reuses the cached location.

Sunrise and sunset data comes from `https://api.sunrise-sunset.org/json`. The API requires attribution for public use; this project uses it for personal desktop automation.

## Configuration

You do not need a config file. Create `~/.config/auto-theme-switcher/config.json` only if you want to set your location manually or change the themes:

```json
{
  "location": {
    "lat": 50.45,
    "lng": 30.52
  },
  "themes": {
    "light": {
      "color-scheme": "prefer-light",
      "gtk-theme": "Yaru",
      "icon-theme": "Yaru"
    },
    "dark": {
      "color-scheme": "prefer-dark",
      "gtk-theme": "Yaru-dark",
      "icon-theme": "Yaru-dark"
    }
  }
}
```

If you set `location.lat` and `location.lng`, the script skips IP-based location lookup.

## Manual usage

Print the theme that would be selected:

```bash
./auto_theme_switcher.py --print-only
```

Apply the selected theme once:

```bash
./auto_theme_switcher.py
```