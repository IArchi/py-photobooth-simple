#!/bin/bash
# Run as the desktop user, not root: bash tools/setup_boot_branding.sh [logo.svg] [1024x600]
set -euo pipefail

configure_branding_files() {
    # python3 is already part of the photobooth installation; preserve unrelated settings.
    python3 - "$@" <<'PY'
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile


def write(path, content):
    path = Path(path)
    if path.exists() and path.read_text() == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(path.name + '.before-photobooth')
        if not backup.exists():
            shutil.copy2(path, backup)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, path.stat().st_mode & 0o777 if path.exists() else 0o644)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def update_ini(path, section, settings):
    path = Path(path)
    lines = path.read_text().splitlines() if path.exists() else []
    header = '[' + section + ']'
    start = next((i for i, line in enumerate(lines) if line.strip() == header), None)
    if start is None:
        lines += ['', header]
        start = len(lines) - 1
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].strip().startswith('[')), len(lines))
    # Only replace keys in this section, retaining comments and desktop icon positions.
    body = [line for line in lines[start + 1:end]
            if line.split('=', 1)[0].strip() not in settings]
    body += [key + '=' + value for key, value in settings.items()]
    write(path, '\n'.join(lines[:start + 1] + body + lines[end:]) + '\n')


def configure_boot(directory):
    cmdline = directory / 'cmdline.txt'
    tokens = cmdline.read_text().split()
    if not any(token.startswith('root=') for token in tokens):
        raise ValueError('cmdline.txt sans root= : modification refusee')
    options = ['quiet', 'splash', 'logo.nologo', 'loglevel=3',
               'systemd.show_status=false', 'vt.global_cursor_default=0']
    keys = {option.split('=', 1)[0] for option in options}
    tokens = [token for token in tokens if token.split('=', 1)[0] not in keys]
    tokens = ['console=tty3' if token == 'console=tty1' else token for token in tokens]
    write(cmdline, ' '.join(dict.fromkeys(tokens + options)) + '\n')
    config = directory / 'config.txt'
    original = config.read_text()
    begin = '# BEGIN Photobooth boot branding'
    end = '# END Photobooth boot branding'
    original = re.sub(re.escape(begin) + r'\n.*?' + re.escape(end) + r'\n?',
                      '', original, flags=re.S).rstrip()
    # Append a global section so earlier model-specific settings cannot override it.
    write(config, original + '\n\n' + begin + '\n[all]\n'
          'disable_splash=1\nauto_initramfs=1\n' + end + '\n')


def configure_desktop(directory, wallpaper):
    # ponytail: target Raspberry Pi OS's native desktop, not arbitrary compositors.
    # Add another backend here only if the deployed desktop changes.
    profiles = {'LXDE-pi', 'default'}
    profiles.update(path.name for path in (directory / 'pcmanfm').glob('*') if path.is_dir())
    for profile in sorted(profiles):
        folder = directory / 'pcmanfm' / profile
        desktops = set(folder.glob('desktop-items-*.conf')) | {folder / 'desktop-items-0.conf'}
        for desktop in desktops:
            update_ini(desktop, '*', {'wallpaper': wallpaper, 'wallpaper_mode': 'fit',
                                     'wallpaper_common': '1', 'desktop_bg': '#1d4438'})
    update_ini(directory / 'wf-shell.ini', 'background',
               {'image': wallpaper, 'fill_mode': 'preserve_aspect', 'fade_duration': '0'})
    # Disable the old autostart too when upgrading an existing installation.
    # PCManFM's wallpaper API opens an alert if its desktop manager is not ready
    # (or wf-background owns the desktop). Configuration is loaded next login.
    write(directory / 'autostart' / 'photobooth-wallpaper.desktop',
          '[Desktop Entry]\nType=Application\nName=Photobooth wallpaper\n'
          'Hidden=true\n')


if __name__ == '__main__':
    mode, directory, *extra = sys.argv[1:]
    if mode == 'boot':
        configure_boot(Path(directory))
    elif mode == 'desktop':
        configure_desktop(Path(directory), extra[0])
    else:
        raise ValueError('Mode inconnu : ' + mode)
PY
}

main() {
    if [[ "${1:-}" == --help || "${1:-}" == -h ]]; then
        printf 'Usage: bash %s [logo.svg] [largeurxhauteur]\n' "$0"
        printf 'Defaut : favicon.svg, 1024x600. Executer sans sudo.\n'
        return
    fi
    if [[ "$EUID" -eq 0 ]]; then
        printf 'Executer sans sudo, avec le compte qui ouvre le bureau.\n' >&2
        return 1
    fi
    if [[ "$(uname -s)" != Linux ]] || ! grep -q 'Raspberry Pi' /proc/device-tree/model 2>/dev/null; then
        printf 'Ce script doit etre execute sur le Raspberry Pi.\n' >&2
        return 1
    fi
    # auto_initramfs is supported by current Raspberry Pi OS boot firmware.
    if ! grep -Eq '^VERSION_CODENAME=(bookworm|trixie)$' /etc/os-release; then
        printf 'Ce script cible Raspberry Pi OS Bookworm ou Trixie.\n' >&2
        return 1
    fi
    if [[ $# -gt 2 ]]; then
        printf 'Trop de parametres. Utiliser --help.\n' >&2
        return 1
    fi
    local project logo size width height boot config temp theme
    project="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
    logo="${1:-$project/favicon.svg}"
    size="${2:-1024x600}"
    if [[ ! -f "$logo" || ! "$size" =~ ^([1-9][0-9]{2,3})x([1-9][0-9]{2,3})$ ]]; then
        printf 'Logo absent ou resolution invalide (exemple : 1024x600).\n' >&2
        return 1
    fi
    width="${BASH_REMATCH[1]}"
    height="${BASH_REMATCH[2]}"
    boot=/boot/firmware
    [[ -f "$boot/cmdline.txt" ]] || boot=/boot
    if [[ ! -f "$boot/cmdline.txt" || ! -f "$boot/config.txt" ]]; then
        printf 'Fichiers de demarrage Raspberry Pi OS introuvables.\n' >&2
        return 1
    fi
    if ! command -v pcmanfm >/dev/null && ! command -v wf-background >/dev/null; then
        printf 'Bureau non pris en charge : PCManFM ou wf-background requis.\n' >&2
        return 1
    fi
    sudo -v
    sudo apt-get update
    sudo apt-get install -y plymouth plymouth-themes initramfs-tools librsvg2-bin python3-pil

    temp="$(mktemp -d)"
    trap "rm -rf -- $(printf '%q' "$temp")" EXIT
    # rsvg uses installed fonts, never the SVG's Google Fonts import.
    if grep -q '<text' "$logo"; then
        printf 'Attention : textes SVG rendus avec les polices locales. Convertir en chemins pour un rendu exact.\n'
    fi
    rsvg-convert --keep-aspect-ratio -w "$((width / 2))" -h "$((height * 2 / 5))" \
        "$logo" -o "$temp/logo.png"
    /usr/bin/python3 - "$temp" "$width" "$height" <<'PY'
from pathlib import Path
import sys
from PIL import Image

directory = Path(sys.argv[1])
width, height = map(int, sys.argv[2:])
canvas = Image.new('RGB', (width, height), '#1d4438')
with Image.open(directory / 'logo.png').convert('RGBA') as logo:
    canvas.paste(logo, ((width - logo.width) // 2, (height - logo.height) // 2), logo)
canvas.save(directory / 'wallpaper.png')
PY
    theme=/usr/share/plymouth/themes/photobooth
    cat > "$temp/photobooth.plymouth" <<'EOF'
[Plymouth Theme]
Name=Photobooth
Description=Photobooth start up
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/photobooth
ScriptFile=/usr/share/plymouth/themes/photobooth/photobooth.script
EOF
    cat > "$temp/photobooth.script" <<'EOF'
Window.SetBackgroundTopColor(0.11372549, 0.26666667, 0.21960784);
Window.SetBackgroundBottomColor(0.11372549, 0.26666667, 0.21960784);
image = Image("wallpaper.png");
scale = Math.Min(Window.GetWidth() / image.GetWidth(), Window.GetHeight() / image.GetHeight());
image = image.Scale(image.GetWidth() * scale, image.GetHeight() * scale);
sprite = Sprite(image);
sprite.SetX((Window.GetWidth() - image.GetWidth()) / 2);
sprite.SetY((Window.GetHeight() - image.GetHeight()) / 2);
EOF
    sudo install -d "$theme"
    sudo install -m 644 "$temp/photobooth.plymouth" "$temp/photobooth.script" "$temp/wallpaper.png" "$theme/"
    # Keep the wallpaper outside the theme as well, independent of Plymouth cleanup.
    sudo install -d /usr/share/backgrounds/photobooth
    sudo install -m 644 "$temp/wallpaper.png" /usr/share/backgrounds/photobooth/wallpaper.png

    # Rebuild before changing boot parameters; a failure leaves the boot files intact.
    sudo plymouth-set-default-theme -R photobooth
    # Pass only this helper to a privileged shell, never the full installer.
    { declare -f configure_branding_files; printf '\nconfigure_branding_files boot %q\n' "$boot"; } | sudo bash
    config="${XDG_CONFIG_HOME:-$HOME/.config}"
    configure_branding_files desktop "$config" /usr/share/backgrounds/photobooth/wallpaper.png
    rm -rf -- "$temp"
    trap - EXIT
    printf '\nConfiguration terminee. Sauvegardes : *.before-photobooth a cote des fichiers modifies.\n'
    printf 'Redemarrer avec : sudo reboot\n'
    printf 'Fond configure pour la prochaine session ; aucun appel au gestionnaire du bureau en cours.\n'
    printf 'Connexion automatique et lancement du photobooth inchanges. Les diagnostics du bootloader restent distincts.\n'
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
