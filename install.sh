#!/usr/bin/env bash
set -euo pipefail

app_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
systemd_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
autostart_dir="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"

mkdir -p "$systemd_dir" "$autostart_dir"

cat > "$systemd_dir/auto-theme-switcher.service" <<SERVICE
[Unit]
Description=Apply GNOME light/dark theme based on sunrise and sunset
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=$app_dir/auto_theme_switcher.py
SERVICE

cat > "$systemd_dir/auto-theme-switcher.timer" <<TIMER
[Unit]
Description=Check GNOME theme against sunrise and sunset

[Timer]
OnBootSec=2min
OnUnitActiveSec=10min
Persistent=true

[Install]
WantedBy=timers.target
TIMER

cat > "$autostart_dir/auto-theme-switcher.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Auto Theme Switcher
Exec=systemctl --user start auto-theme-switcher.service
NoDisplay=true
X-GNOME-Autostart-enabled=true
DESKTOP

chmod +x "$app_dir/auto_theme_switcher.py"
systemctl --user daemon-reload
systemctl --user enable --now auto-theme-switcher.timer
if ! systemctl --user start auto-theme-switcher.service; then
    echo "Installed, but the initial theme check failed. Check: journalctl --user -u auto-theme-switcher.service -n 50" >&2
fi

echo "Installed auto-theme-switcher user service, timer, and GNOME autostart entry."
