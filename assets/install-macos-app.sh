#!/usr/bin/env bash

# OpenManus macOS desktop app installer.
#
# Usage:
#   bash assets/install-macos-app.sh
#
# The installer creates a small .app bundle that opens Terminal and runs
# OpenManus from the current checkout.

set -euo pipefail

APP_NAME="OpenManus"
PRIMARY_INSTALL_DIR="/Applications"
FALLBACK_INSTALL_DIR="${HOME}/Applications"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ICON_PATH="${PROJECT_ROOT}/assets/logo.jpg"
LAUNCH_SCRIPT="${PROJECT_ROOT}/main.py"

info() { printf '[OpenManus] %s\n' "$1"; }
warn() { printf '[OpenManus] Warning: %s\n' "$1"; }
fail() { printf '[OpenManus] Error: %s\n' "$1" >&2; exit 1; }

if [[ "$(uname -s)" != "Darwin" ]]; then
    fail "This installer only supports macOS."
fi

command -v osacompile >/dev/null 2>&1 || fail "osacompile is required on macOS."

if [ ! -f "${LAUNCH_SCRIPT}" ]; then
    fail "main.py was not found at ${LAUNCH_SCRIPT}."
fi

project_path_for_applescript="${PROJECT_ROOT}/"
project_path_for_applescript="${project_path_for_applescript//\\/\\\\}"
project_path_for_applescript="${project_path_for_applescript//\"/\\\"}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

info "Building ${APP_NAME}.app..."

cat > "${TMP_DIR}/${APP_NAME}.applescript" <<APPLESCRIPT
on run
    set projectPathStr to "${project_path_for_applescript}"
    tell application "Terminal"
        activate
        set launchCommand to "cd " & quoted form of projectPathStr & " && clear && echo 'Starting OpenManus' && if [ -x .venv/bin/python ]; then .venv/bin/python main.py; elif command -v uv >/dev/null 2>&1; then uv run python main.py; else python3 main.py; fi"
        do script launchCommand
    end tell
end run
APPLESCRIPT

osacompile -o "${TMP_DIR}/${APP_NAME}.app" "${TMP_DIR}/${APP_NAME}.applescript"

if [ -f "${ICON_PATH}" ] && command -v sips >/dev/null 2>&1 && command -v iconutil >/dev/null 2>&1; then
    info "Applying icon from assets/logo.jpg..."
    ICONSET_DIR="${TMP_DIR}/openmanus.iconset"
    mkdir -p "${ICONSET_DIR}"

    sips -z 16 16 "${ICON_PATH}" --out "${ICONSET_DIR}/icon_16x16.png" >/dev/null
    sips -z 32 32 "${ICON_PATH}" --out "${ICONSET_DIR}/icon_16x16@2x.png" >/dev/null
    sips -z 32 32 "${ICON_PATH}" --out "${ICONSET_DIR}/icon_32x32.png" >/dev/null
    sips -z 64 64 "${ICON_PATH}" --out "${ICONSET_DIR}/icon_32x32@2x.png" >/dev/null
    sips -z 128 128 "${ICON_PATH}" --out "${ICONSET_DIR}/icon_128x128.png" >/dev/null
    sips -z 256 256 "${ICON_PATH}" --out "${ICONSET_DIR}/icon_128x128@2x.png" >/dev/null
    sips -z 256 256 "${ICON_PATH}" --out "${ICONSET_DIR}/icon_256x256.png" >/dev/null
    sips -z 512 512 "${ICON_PATH}" --out "${ICONSET_DIR}/icon_256x256@2x.png" >/dev/null
    sips -z 512 512 "${ICON_PATH}" --out "${ICONSET_DIR}/icon_512x512.png" >/dev/null
    cp "${ICON_PATH}" "${ICONSET_DIR}/icon_512x512@2x.png"

    iconutil -c icns "${ICONSET_DIR}" -o "${TMP_DIR}/openmanus.icns"
    cp "${TMP_DIR}/openmanus.icns" "${TMP_DIR}/${APP_NAME}.app/Contents/Resources/applet.icns"
else
    warn "Icon tooling or assets/logo.jpg not found; using the default app icon."
fi

install_bundle() {
    local install_dir="$1"
    local destination="${install_dir}/${APP_NAME}.app"

    mkdir -p "${install_dir}"
    rm -rf "${destination}"
    cp -R "${TMP_DIR}/${APP_NAME}.app" "${destination}"
    printf '%s\n' "${destination}"
}

install_path=""
if install_path="$(install_bundle "${PRIMARY_INSTALL_DIR}" 2>/dev/null)"; then
    :
else
    warn "Could not write to ${PRIMARY_INSTALL_DIR}; installing to ${FALLBACK_INSTALL_DIR}."
    install_path="$(install_bundle "${FALLBACK_INSTALL_DIR}")"
fi

info "Installed to ${install_path}"
info "Launch it from Spotlight, Launchpad, Finder, or with: open '${install_path}'"
info "If you move this checkout, run this installer again so the app points to the new path."
