#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

die() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

# Always ask for a selection, even when only one item is available.
choose() {
    local item
    PS3="Enter a number: "
    select item in "$@"; do
        if [[ -n "$item" ]]; then
            SELECTED="$item"
            return
        fi
        printf 'Invalid selection. Try again.\n' >&2
    done
    die "No selection made."
}

command -v apt-get >/dev/null || die "This script requires Debian OS."

sudo apt-get update
sudo apt-get install -y cups printer-driver-gutenprint
sudo systemctl enable --now cups

printf '\nDiscovering connected USB printers...\n'
DEVICES="$(sudo lpinfo -v)"

mapfile -t PRINTERS < <(
    printf '%s\n' "$DEVICES" |
        awk '$1 == "direct" &&
             $2 ~ /^(usb|gutenprint[^:]*\+usb):\/\// { print $2 }'
)

((${#PRINTERS[@]} > 0)) ||
    die "No USB printer found. Check the power and USB connection."

printf '\nSelect a printer:\n'
choose "${PRINTERS[@]}"
URI="$SELECTED"

# Normalize a copy for model detection; preserve the original connection URI.
DEVICE_KEY="$(
    printf '%s' "${URI%%\?*}" |
        LC_ALL=C tr '[:upper:]' '[:lower:]' |
        LC_ALL=C tr -cd 'a-z0-9'
)"

if [[ "$DEVICE_KEY" == *ds620* ]]; then
    DEFAULT_QUEUE="DNP_DS620"
    PPD="$SCRIPT_DIR/docs/DNP-DS620.ppd"
    [[ -r "$PPD" ]] || die "Cannot read PPD: $PPD"

    DRIVER_ARGS=(-P "$PPD" -o PageSize=w288h432-div2)
    printf '\nUsing the DNP DS620 PPD: %s\n' "$PPD"
else
    printf '\nLoading installed Gutenprint drivers...\n'
    MODELS="$(sudo lpinfo -m)"
    mapfile -t GUTENPRINT_DRIVERS < <(
        printf '%s\n' "$MODELS" |
            awk 'tolower($0) ~ /gutenprint/'
    )

    ((${#GUTENPRINT_DRIVERS[@]} > 0)) ||
        die "No Gutenprint drivers are installed."

    while true; do
        printf '\n'
        read -r -p \
            "Search drivers by model (leave empty to list all): " SEARCH

        MATCHES=()
        for DRIVER in "${GUTENPRINT_DRIVERS[@]}"; do
            if [[ "${DRIVER,,}" == *"${SEARCH,,}"* ]]; then
                MATCHES+=("$DRIVER")
            fi
        done

        if ((${#MATCHES[@]} > 0)); then
            break
        fi
        printf 'No matching driver. Try another search.\n'
    done

    printf '\nSelect the driver matching your printer:\n'
    choose "${MATCHES[@]}"
    MODEL="${SELECTED%% *}"

    DRIVER_ARGS=(-m "$MODEL")
    DEFAULT_QUEUE="USB_Printer"
fi

printf '\n'
read -r -p "CUPS queue name [$DEFAULT_QUEUE]: " QUEUE
QUEUE="${QUEUE:-$DEFAULT_QUEUE}"

[[ "$QUEUE" =~ ^[a-zA-Z0-9_-]+$ ]] ||
    die "Use only letters, digits, underscores and hyphens for the queue name."

printf '\nQueue: %s\nConnection: %s\n' "$QUEUE" "$URI"
printf 'An existing queue with this name will be updated.\n'
read -r -p "Apply this configuration? [y/N]: " CONFIRM
[[ "$CONFIRM" =~ ^[yY]$ ]] || exit 0

sudo lpadmin \
    -p "$QUEUE" \
    -v "$URI" \
    "${DRIVER_ARGS[@]}" \
    -o printer-is-shared=false \
    -E

sudo cupsaccept "$QUEUE"

printf '\nPrinter configured successfully.\n'
lpstat -p "$QUEUE" -v

printf '\nAvailable printer options, including paper sizes:\n'
lpoptions -p "$QUEUE" -l