#!/usr/bin/env bash
set -euo pipefail

systemd_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
autostart_dir="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"

systemctl --user disable --now auto-theme-switcher.timer 2>/dev/null || true
rm -f "$systemd_dir/auto-theme-switcher.service"
rm -f "$systemd_dir/auto-theme-switcher.timer"
rm -f "$autostart_dir/auto-theme-switcher.desktop"
systemctl --user daemon-reload

echo "Removed auto-theme-switcher user service, timer, and GNOME autostart entry."
