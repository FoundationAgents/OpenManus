#!/bin/sh
# shellcheck shell=dash
# shellcheck disable=SC2039  # local is non-POSIX
#
# Licensed under the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

# This runs on Unix shells like bash/dash/ksh/zsh. It uses the common `local`
# extension. Note: Most shells limit `local` to 1 var per line, contra bash.

# Some versions of ksh have no `local` keyword. Alias it to `typeset`, but
# beware this makes variables global with f()-style function syntax in ksh93.
# mksh has this alias by default.
has_local() {
    # shellcheck disable=SC2034  # deliberately unused
    local _has_local
}

has_local 2>/dev/null || alias local=typeset

set -u

APP_NAME="uv"
APP_VERSION="0.8.0"
# Look for GitHub Enterprise-style base URL first
if [ -n "${UV_INSTALLER_GHE_BASE_URL:-}" ]; then
    INSTALLER_BASE_URL="$UV_INSTALLER_GHE_BASE_URL"
else
    INSTALLER_BASE_URL="${UV_INSTALLER_GITHUB_BASE_URL:-https://github.com}"
fi
if [ -n "${INSTALLER_DOWNLOAD_URL:-}" ]; then
    ARTIFACT_DOWNLOAD_URL="$INSTALLER_DOWNLOAD_URL"
else
    ARTIFACT_DOWNLOAD_URL="${INSTALLER_BASE_URL}/astral-sh/uv/releases/download/0.8.0"
fi
PRINT_VERBOSE=${INSTALLER_PRINT_VERBOSE:-0}
PRINT_QUIET=${INSTALLER_PRINT_QUIET:-0}
if [ -n "${UV_NO_MODIFY_PATH:-}" ]; then
    NO_MODIFY_PATH="$UV_NO_MODIFY_PATH"
else
    NO_MODIFY_PATH=${INSTALLER_NO_MODIFY_PATH:-0}
fi
if [ "${UV_DISABLE_UPDATE:-0}" = "1" ]; then
    INSTALL_UPDATER=0
else
    INSTALL_UPDATER=1
fi
UNMANAGED_INSTALL="${UV_UNMANAGED_INSTALL:-}"
if [ -n "${UNMANAGED_INSTALL}" ]; then
    NO_MODIFY_PATH=1
    INSTALL_UPDATER=0
fi
AUTH_TOKEN="${UV_GITHUB_TOKEN:-}"

read -r RECEIPT <<EORECEIPT
{"binaries":["CARGO_DIST_BINS"],"binary_aliases":{},"cdylibs":["CARGO_DIST_DYLIBS"],"cstaticlibs":["CARGO_DIST_STATICLIBS"],"install_layout":"unspecified","install_prefix":"AXO_INSTALL_PREFIX","modify_path":true,"provider":{"source":"cargo-dist","version":"0.28.7-prerelease.1"},"source":{"app_name":"uv","name":"uv","owner":"astral-sh","release_type":"github"},"version":"0.8.0"}
EORECEIPT

# Some Linux distributions don't set HOME
# https://github.com/astral-sh/uv/issues/6965#issuecomment-2915796022
get_home() {
    if [ -n "${HOME:-}" ]; then
        echo "$HOME"
    elif [ -n "${USER:-}" ]; then
        getent passwd "$USER" | cut -d: -f6
    else
        getent passwd "$(id -un)" | cut -d: -f6
    fi
}
# The HOME reference to show in user output. If `$HOME` isn't set, we show the absolute path instead.
get_home_expression() {
    if [ -n "${HOME:-}" ]; then
        # shellcheck disable=SC2016
        echo '$HOME'
    elif [ -n "${USER:-}" ]; then
        getent passwd "$USER" | cut -d: -f6
    else
        getent passwd "$(id -un)" | cut -d: -f6
    fi
}
INFERRED_HOME=$(get_home)
# shellcheck disable=SC2034
INFERRED_HOME_EXPRESSION=$(get_home_expression)
RECEIPT_HOME="${XDG_CONFIG_HOME:-$INFERRED_HOME/.config}/uv"

usage() {
    # print help (this cat/EOF stuff is a "heredoc" string)
    cat <<EOF
uv-installer.sh

The installer for uv 0.8.0

This script detects what platform you're on and fetches an appropriate archive from
https://github.com/astral-sh/uv/releases/download/0.8.0
then unpacks the binaries and installs them to the first of the following locations

    \$XDG_BIN_HOME
    \$XDG_DATA_HOME/../bin
    \$HOME/.local/bin

It will then add that dir to PATH by adding the appropriate line to your shell profiles.

USAGE:
    uv-installer.sh [OPTIONS]

OPTIONS:
    -v, --verbose
            Enable verbose output

    -q, --quiet
            Disable progress output

        --no-modify-path
            Don't configure the PATH environment variable

    -h, --help
            Print help information
EOF
}

download_binary_and_run_installer() {
    downloader --check
    need_cmd uname
    need_cmd mktemp
    need_cmd chmod
    need_cmd mkdir
    need_cmd rm
    need_cmd tar
    need_cmd grep
    need_cmd cat

    for arg in "$@"; do
        case "$arg" in
            --help)
                usage
                exit 0
                ;;
            --quiet)
                PRINT_QUIET=1
                ;;
            --verbose)
                PRINT_VERBOSE=1
                ;;
            --no-modify-path)
                say "--no-modify-path has been deprecated; please set UV_NO_MODIFY_PATH=1 in the environment"
                NO_MODIFY_PATH=1
                ;;
            *)
                OPTIND=1
                if [ "${arg%%--*}" = "" ]; then
                    err "unknown option $arg"
                fi
                while getopts :hvq sub_arg "$arg"; do
                    case "$sub_arg" in
                        h)
                            usage
                            exit 0
                            ;;
                        v)
                            # user wants to skip the prompt --
                            # we don't need /dev/tty
                            PRINT_VERBOSE=1
                            ;;
                        q)
                            # user wants to skip the prompt --
                            # we don't need /dev/tty
                            PRINT_QUIET=1
                            ;;
                        *)
                            err "unknown option -$OPTARG"
                            ;;
                        esac
                done
                ;;
        esac
    done

    get_architecture || return 1
    local _true_arch="$RETVAL"
    assert_nz "$_true_arch" "arch"
    local _cur_arch="$_true_arch"


    # look up what archives support this platform
    local _artifact_name
    _artifact_name="$(select_archive_for_arch "$_true_arch")" || return 1
    local _bins
    local _zip_ext
    local _arch
    local _checksum_style
    local _checksum_value

    # destructure selected archive info into locals
    case "$_artifact_name" in
        "uv-aarch64-apple-darwin.tar.gz")
            _arch="aarch64-apple-darwin"
            _zip_ext=".tar.gz"
            _bins="uv uvx"
            _bins_js_array='"uv","uvx"'
            _libs=""
            _libs_js_array=""
            _staticlibs=""
            _staticlibs_js_array=""
            _updater_name=""
            _updater_bin=""
            ;;
        "uv-aarch64-pc-windows-msvc.zip")
            _arch="aarch64-pc-windows-msvc"
            _zip_ext=".zip"
            _bins="uv.exe uvx.exe uvw.exe"
            _bins_js_array='"uv.exe","uvx.exe","uvw.exe"'
            _libs=""
            _libs_js_array=""
            _staticlibs=""
            _staticlibs_js_array=""
            _updater_name=""
            _updater_bin=""
            ;;
        "uv-aarch64-unknown-linux-gnu.tar.gz")
            _arch="aarch64-unknown-linux-gnu"
            _zip_ext=".tar.gz"
            _bins="uv uvx"
            _bins_js_array='"uv","uvx"'
            _libs=""
            _libs_js_array=""
            _staticlibs=""
            _staticlibs_js_array=""
            _updater_name=""
            _updater_bin=""
            ;;
        "uv-aarch64-unknown-linux-musl.tar.gz")
            _arch="aarch64-unknown-linux-musl-static"
            _zip_ext=".tar.gz"
            _bins="uv uvx"
            _bins_js_array='"uv","uvx"'
            _libs=""
            _libs_js_array=""
            _staticlibs=""
            _staticlibs_js_array=""
            _updater_name=""
            _updater_bin=""
            ;;
        "uv-arm-unknown-linux-musleabihf.tar.gz")
            _arch="arm-unknown-linux-musl-staticeabihf"
            _zip_ext=".tar.gz"
            _bins="uv uvx"
            _bins_js_array='"uv","uvx"'
            _libs=""
            _libs_js_array=""
            _staticlibs=""
            _staticlibs_js_array=""
            _updater_name=""
            _updater_bin=""
            ;;
        "uv-armv7-unknown-linux-gnueabihf.tar.gz")
            _arch="armv7-unknown-linux-gnueabihf"
            _zip_ext=".tar.gz"
            _bins="uv uvx"
            _bins_js_array='"uv","uvx"'
            _libs=""
            _libs_js_array=""
            _staticlibs=""
            _staticlibs_js_array=""
            _updater_name=""
            _updater_bin=""
            ;;
        "uv-armv7-unknown-linux-musleabihf.tar.gz")
            _arch="armv7-unknown-linux-musl-staticeabihf"
            _zip_ext=".tar.gz"
            _bins="uv uvx"
            _bins_js_array='"uv","uvx"'
            _libs=""
            _libs_js_array=""
            _staticlibs=""
            _staticlibs_js_array=""
            _updater_name=""
            _updater_bin=""
            ;;
        "uv-i686-pc-windows-msvc.zip")
            _arch="i686-pc-windows-msvc"
            _zip_ext=".zip"
            _bins="uv.exe uvx.exe uvw.exe"
            _bins_js_array='"uv.exe","uvx.exe","uvw.exe"'
            _libs=""
            _libs_js_array=""
            _staticlibs=""
            _staticlibs_js_array=""
            _updater_name=""
            _updater_bin=""
            ;;
        "uv-i686-unknown-linux-gnu.tar.gz")
            _arch="i686-unknown-linux-gnu"
            _zip_ext=".tar.gz"
            _bins="uv uvx"
            _bins_js_array='"uv","uvx"'
            _libs=""
            _libs_js_array=""
            _staticlibs=""
            _staticlibs_js_array=""
            _updater_name=""
            _updater_bin=""
            ;;
        "uv-i686-unknown-linux-musl.tar.gz")
            _arch="i686-unknown-linux-musl-static"
            _zip_ext=".tar.gz"
            _bins="uv uvx"
            _bins_js_array='"uv","uvx"'
            _libs=""
            _libs_js_array=""
            _staticlibs=""
            _staticlibs_js_array=""
            _updater_name=""
            _updater_bin=""
            ;;
        "uv-powerpc64-unknown-linux-gnu.tar.gz")
            _arch="powerpc64-unknown-linux-gnu"
            _zip_ext=".tar.gz"
            _bins="uv uvx"
            _bins_js_array='"uv","uvx"'
            _libs=""
            _libs_js_array=""
            _staticlibs=""
            _staticlibs_js_array=""
            _updater_name=""
            _updater_bin=""
            ;;
        "uv-powerpc64le-unknown-linux-gnu.tar.gz")
            _arch="powerpc64le-unknown-linux-gnu"
            _zip_ext=".tar.gz"
            _bins="uv uvx"
            _bins_js_array='"uv","uvx"'
            _libs=""
            _libs_js_array=""
            _staticlibs=""
            _staticlibs_js_array=""
            _updater_name=""
            _updater_bin=""
            ;;
        "uv-riscv64gc-unknown-linux-gnu.tar.gz")
            _arch="riscv64gc-unknown-linux-gnu"
            _zip_ext=".tar.gz"
            _bins="uv uvx"
            _bins_js_array='"uv","uvx"'
            _libs=""
            _libs_js_array=""
            _staticlibs=""
            _staticlibs_js_array=""
            _updater_name=""
            _updater_bin=""
            ;;
        "uv-s390x-unknown-linux-gnu.tar.gz")
            _arch="s390x-unknown-linux-gnu"
            _zip_ext=".tar.gz"
            _bins="uv uvx"
            _bins_js_array='"uv","uvx"'
            _libs=""
            _libs_js_array=""
            _staticlibs=""
            _staticlibs_js_array=""
            _updater_name=""
            _updater_bin=""
            ;;
        "uv-x86_64-apple-darwin.tar.gz")
            _arch="x86_64-apple-darwin"
            _zip_ext=".tar.gz"
            _bins="uv uvx"
            _bins_js_array='"uv","uvx"'
            _libs=""
            _libs_js_array=""
            _staticlibs=""
            _staticlibs_js_array=""
            _updater_name=""
            _updater_bin=""
            ;;
        "uv-x86_64-pc-windows-msvc.zip")
            _arch="x86_64-pc-windows-msvc"
            _zip_ext=".zip"
            _bins="uv.exe uvx.exe uvw.exe"
            _bins_js_array='"uv.exe","uvx.exe","uvw.exe"'
            _libs=""
            _libs_js_array=""
            _staticlibs=""
            _staticlibs_js_array=""
            _updater_name=""
            _updater_bin=""
            ;;
        "uv-x86_64-unknown-linux-gnu.tar.gz")
            _arch="x86_64-unknown-linux-gnu"
            _zip_ext=".tar.gz"
            _bins="uv uvx"
            _bins_js_array='"uv","uvx"'
            _libs=""
            _libs_js_array=""
            _staticlibs=""
            _staticlibs_js_array=""
            _updater_name=""
            _updater_bin=""
            ;;
        "uv-x86_64-unknown-linux-musl.tar.gz")
            _arch="x86_64-unknown-linux-musl-static"
            _zip_ext=".tar.gz"
            _bins="uv uvx"
            _bins_js_array='"uv","uvx"'
            _libs=""
            _libs_js_array=""
            _staticlibs=""
            _staticlibs_js_array=""
            _updater_name=""
            _updater_bin=""
            ;;
        *)
            err "internal installer error: selected download $_artifact_name doesn't exist!?"
            ;;
    esac


    # Replace the placeholder binaries with the calculated array from above
    RECEIPT="$(echo "$RECEIPT" | sed s/'"CARGO_DIST_BINS"'/"$_bins_js_array"/)"
    RECEIPT="$(echo "$RECEIPT" | sed s/'"CARGO_DIST_DYLIBS"'/"$_libs_js_array"/)"
    RECEIPT="$(echo "$RECEIPT" | sed s/'"CARGO_DIST_STATICLIBS"'/"$_staticlibs_js_array"/)"

    # download the archive
    local _url="$ARTIFACT_DOWNLOAD_URL/$_artifact_name"
    local _dir
    _dir="$(ensure mktemp -d)" || return 1
    local _file="$_dir/input$_zip_ext"

    say "downloading $APP_NAME $APP_VERSION ${_arch}" 1>&2
    say_verbose "  from $_url" 1>&2
    say_verbose "  to $_file" 1>&2

    ensure mkdir -p "$_dir"

    if ! downloader "$_url" "$_file"; then
      say "failed to download $_url"
      say "this may be a standard network error, but it may also indicate"
      say "that $APP_NAME's release process is not working. When in doubt"
      say "please feel free to open an issue!"
      exit 1
    fi

    if [ -n "${_checksum_style:-}" ]; then
        verify_checksum "$_file" "$_checksum_style" "$_checksum_value"
    else
        say "no checksums to verify"
    fi

    # ...and then the updater, if it exists
    if [ -n "$_updater_name" ] && [ "$INSTALL_UPDATER" = "1" ]; then
        local _updater_url="$ARTIFACT_DOWNLOAD_URL/$_updater_name"
        # This renames the artifact while doing the download, removing the
        # target triple and leaving just the appname-update format
        local _updater_file="$_dir/$APP_NAME-update"

        if ! downloader "$_updater_url" "$_updater_file"; then
          say "failed to download $_updater_url"
          say "this may be a standard network error, but it may also indicate"
          say "that $APP_NAME's release process is not working. When in doubt"
          say "please feel free to open an issue!"
          exit 1
        fi

        # Add the updater to the list of binaries to install
        _bins="$_bins $APP_NAME-update"
    fi

    # unpack the archive
    case "$_zip_ext" in
        ".zip")
            ensure unzip -q "$_file" -d "$_dir"
            ;;

        ".tar."*)
            ensure tar xf "$_file" --strip-components 1 -C "$_dir"
            ;;
        *)
            err "unknown archive format: $_zip_ext"
            ;;
    esac

    install "$_dir" "$_bins" "$_libs" "$_staticlibs" "$_arch" "$@"
    local _retval=$?
    if [ "$_retval" != 0 ]; then
        return "$_retval"
    fi

    ignore rm -rf "$_dir"

    # Install the install receipt
    if [ "$INSTALL_UPDATER" = "1" ]; then
        if ! mkdir -p "$RECEIPT_HOME"; then
            err "unable to create receipt directory at $RECEIPT_HOME"
        else
            echo "$RECEIPT" > "$RECEIPT_HOME/$APP_NAME-receipt.json"
            # shellcheck disable=SC2320
            local _retval=$?
        fi
    else
        local _retval=0
    fi

    return "$_retval"
}

# Replaces $HOME with the variable name for display to the user,
# only if $HOME is defined.
replace_home() {
    local _str="$1"

    if [ -n "${HOME:-}" ]; then
        echo "$_str" | sed "s,$HOME,\$HOME,"
    else
        echo "$_str"
    fi
}

json_binary_aliases() {
    local _arch="$1"

    case "$_arch" in
    "aarch64-apple-darwin")
        echo '{}'
        ;;
    "aarch64-pc-windows-gnu")
        echo '{}'
        ;;
    "aarch64-unknown-linux-gnu")
        echo '{}'
        ;;
    "aarch64-unknown-linux-musl-dynamic")
        echo '{}'
        ;;
    "aarch64-unknown-linux-musl-static")
        echo '{}'
        ;;
    "arm-unknown-linux-gnueabihf")
        echo '{}'
        ;;
    "arm-unknown-linux-musl-dynamiceabihf")
        echo '{}'
        ;;
    "arm-unknown-linux-musl-staticeabihf")
        echo '{}'
        ;;
    "armv7-unknown-linux-gnueabihf")
        echo '{}'
        ;;
    "armv7-unknown-linux-musl-dynamiceabihf")
        echo '{}'
        ;;
    "armv7-unknown-linux-musl-staticeabihf")
        echo '{}'
        ;;
    "i686-pc-windows-gnu")
        echo '{}'
        ;;
    "i686-unknown-linux-gnu")
        echo '{}'
        ;;
    "i686-unknown-linux-musl-dynamic")
        echo '{}'
        ;;
    "i686-unknown-linux-musl-static")
        echo '{}'
        ;;
    "powerpc64-unknown-linux-gnu")
        echo '{}'
        ;;
    "powerpc64le-unknown-linux-gnu")
        echo '{}'
        ;;
    "riscv64gc-unknown-linux-gnu")
        echo '{}'
        ;;
    "s390x-unknown-linux-gnu")
        echo '{}'
        ;;
    "x86_64-apple-darwin")
        echo '{}'
        ;;
    "x86_64-pc-windows-gnu")
        echo '{}'
        ;;
    "x86_64-unknown-linux-gnu")
        echo '{}'
        ;;
    "x86_64-unknown-linux-musl-dynamic")
        echo '{}'
        ;;
    "x86_64-unknown-linux-musl-static")
        echo '{}'
        ;;
    *)
        echo '{}'
        ;;
    esac
}

aliases_for_binary() {
    local _bin="$1"
    local _arch="$2"

    case "$_arch" in
    "aarch64-apple-darwin")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "aarch64-pc-windows-gnu")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "aarch64-unknown-linux-gnu")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "aarch64-unknown-linux-musl-dynamic")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "aarch64-unknown-linux-musl-static")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "arm-unknown-linux-gnueabihf")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "arm-unknown-linux-musl-dynamiceabihf")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "arm-unknown-linux-musl-staticeabihf")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "armv7-unknown-linux-gnueabihf")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "armv7-unknown-linux-musl-dynamiceabihf")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "armv7-unknown-linux-musl-staticeabihf")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "i686-pc-windows-gnu")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "i686-unknown-linux-gnu")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "i686-unknown-linux-musl-dynamic")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "i686-unknown-linux-musl-static")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "powerpc64-unknown-linux-gnu")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "powerpc64le-unknown-linux-gnu")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "riscv64gc-unknown-linux-gnu")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "s390x-unknown-linux-gnu")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "x86_64-apple-darwin")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "x86_64-pc-windows-gnu")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "x86_64-unknown-linux-gnu")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "x86_64-unknown-linux-musl-dynamic")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    "x86_64-unknown-linux-musl-static")
        case "$_bin" in
        *)
            echo ""
            ;;
        esac
        ;;
    *)
        echo ""
        ;;
    esac
}

select_archive_for_arch() {
    local _true_arch="$1"
    local _archive

    # try each archive, checking runtime conditions like libc versions
    # accepting the first one that matches, as it's the best match
    case "$_true_arch" in
        "aarch64-apple-darwin")
            _archive="uv-aarch64-apple-darwin.tar.gz"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            _archive="uv-x86_64-apple-darwin.tar.gz"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "aarch64-pc-windows-gnu")
            _archive="uv-aarch64-pc-windows-msvc.zip"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "aarch64-pc-windows-msvc")
            _archive="uv-aarch64-pc-windows-msvc.zip"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            _archive="uv-x86_64-pc-windows-msvc.zip"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            _archive="uv-i686-pc-windows-msvc.zip"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "aarch64-unknown-linux-gnu")
            _archive="uv-aarch64-unknown-linux-gnu.tar.gz"
            if ! check_glibc "2" "28"; then
                _archive=""
            fi
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            _archive="uv-aarch64-unknown-linux-musl.tar.gz"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "aarch64-unknown-linux-musl-dynamic")
            _archive="uv-aarch64-unknown-linux-musl.tar.gz"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "aarch64-unknown-linux-musl-static")
            _archive="uv-aarch64-unknown-linux-musl.tar.gz"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "arm-unknown-linux-gnueabihf")
            _archive="uv-arm-unknown-linux-musleabihf.tar.gz"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "arm-unknown-linux-musl-dynamiceabihf")
            _archive="uv-arm-unknown-linux-musleabihf.tar.gz"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "arm-unknown-linux-musl-staticeabihf")
            _archive="uv-arm-unknown-linux-musleabihf.tar.gz"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "armv7-unknown-linux-gnueabihf")
            _archive="uv-armv7-unknown-linux-gnueabihf.tar.gz"
            if ! check_glibc "2" "17"; then
                _archive=""
            fi
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            _archive="uv-armv7-unknown-linux-musleabihf.tar.gz"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "armv7-unknown-linux-musl-dynamiceabihf")
            _archive="uv-armv7-unknown-linux-musleabihf.tar.gz"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "armv7-unknown-linux-musl-staticeabihf")
            _archive="uv-armv7-unknown-linux-musleabihf.tar.gz"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "i686-pc-windows-gnu")
            _archive="uv-i686-pc-windows-msvc.zip"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "i686-pc-windows-msvc")
            _archive="uv-i686-pc-windows-msvc.zip"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "i686-unknown-linux-gnu")
            _archive="uv-i686-unknown-linux-gnu.tar.gz"
            if ! check_glibc "2" "17"; then
                _archive=""
            fi
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            _archive="uv-i686-unknown-linux-musl.tar.gz"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "i686-unknown-linux-musl-dynamic")
            _archive="uv-i686-unknown-linux-musl.tar.gz"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "i686-unknown-linux-musl-static")
            _archive="uv-i686-unknown-linux-musl.tar.gz"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "powerpc64-unknown-linux-gnu")
            _archive="uv-powerpc64-unknown-linux-gnu.tar.gz"
            if ! check_glibc "2" "17"; then
                _archive=""
            fi
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "powerpc64le-unknown-linux-gnu")
            _archive="uv-powerpc64le-unknown-linux-gnu.tar.gz"
            if ! check_glibc "2" "17"; then
                _archive=""
            fi
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "riscv64gc-unknown-linux-gnu")
            _archive="uv-riscv64gc-unknown-linux-gnu.tar.gz"
            if ! check_glibc "2" "31"; then
                _archive=""
            fi
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "s390x-unknown-linux-gnu")
            _archive="uv-s390x-unknown-linux-gnu.tar.gz"
            if ! check_glibc "2" "17"; then
                _archive=""
            fi
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "x86_64-apple-darwin")
            _archive="uv-x86_64-apple-darwin.tar.gz"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "x86_64-pc-windows-gnu")
            _archive="uv-x86_64-pc-windows-msvc.zip"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "x86_64-pc-windows-msvc")
            _archive="uv-x86_64-pc-windows-msvc.zip"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            _archive="uv-i686-pc-windows-msvc.zip"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "x86_64-unknown-linux-gnu")
            _archive="uv-x86_64-unknown-linux-gnu.tar.gz"
            if ! check_glibc "2" "17"; then
                _archive=""
            fi
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            _archive="uv-x86_64-unknown-linux-musl.tar.gz"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "x86_64-unknown-linux-musl-dynamic")
            _archive="uv-x86_64-unknown-linux-musl.tar.gz"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        "x86_64-unknown-linux-musl-static")
            _archive="uv-x86_64-unknown-linux-musl.tar.gz"
            if [ -n "$_archive" ]; then
                echo "$_archive"
                return 0
            fi
            ;;
        *)
            err "there isn't a download for your platform $_true_arch"
            ;;
    esac
    err "no compatible downloads were found for your platform $_true_arch"
}

check_glibc() {
    local _min_glibc_major="$1"
    local _min_glibc_series="$2"

    # Parsing version out from line 1 like:
    # ldd (Ubuntu GLIBC 2.35-0ubuntu3.1) 2.35
    _local_glibc="$(ldd --version | awk -F' ' '{ if (FNR<=1) print $NF }')"

    if [ "$(echo "${_local_glibc}" | awk -F. '{ print $1 }')" = "$_min_glibc_major" ] && [ "$(echo "${_local_glibc}" | awk -F. '{ print $2 }')" -ge "$_min_glibc_series" ]; then
        return 0
    else
        say "System glibc version (\`${_local_glibc}') is too old; checking alternatives" >&2
        return 1
    fi
}

# See discussion of late-bound vs early-bound for why we use single-quotes with env vars
# shellcheck disable=SC2016
install() {
    # This code needs to both compute certain paths for itself to write to, and
    # also write them to shell/rc files so that they can look them up to e.g.
    # add them to PATH. This requires an active distinction between paths
    # and expressions that can compute them.
    #
    # The distinction lies in when we want env-vars to be evaluated. For instance
    # if we determine that we want to install to $HOME/.myapp, which do we add
    # to e.g. $HOME/.profile:
    #
    # * early-bound: export PATH="/home/myuser/.myapp:$PATH"
    # * late-bound:  export PATH="$HOME/.myapp:$PATH"
    #
    # In this case most people would prefer the late-bound version, but in other
    # cases the early-bound version might be a better idea. In particular when using
    # other env-vars than $HOME, they are more likely to be only set temporarily
    # for the duration of this install script, so it's more advisable to erase their
    # existence with early-bounding.
    #
    # This distinction is handled by "double-quotes" (early) vs 'single-quotes' (late).
    #
    # However if we detect that "$SOME_VAR/..." is a subdir of $HOME, we try to rewrite
    # it to be '$HOME/...' to get the best of both worlds.
    #
    # This script has a few different variants, the most complex one being the
    # CARGO_HOME version which attempts to install things to Cargo's bin dir,
    # potentially setting up a minimal version if the user hasn't ever installed Cargo.
    #
    # In this case we need to:
    #
    # * Install to $HOME/.cargo/bin/
    # * Create a shell script at $HOME/.cargo/env that:
    #   * Checks if $HOME/.cargo/bin/ is on PATH
    #   * and if not prepends it to PATH
    # * Edits $INFERRED_HOME/.profile to run $HOME/.cargo/env (if the line doesn't exist)
    #
    # To do this we need these 4 values:

    # The actual path we're going to install to
    local _install_dir
    # The directory C dynamic/static libraries install to
    local _lib_install_dir
    # The install prefix we write to the receipt.
    # For organized install methods like CargoHome, which have
    # subdirectories, this is the root without `/bin`. For other
    # methods, this is the same as `_install_dir`.
    local _receipt_install_dir
    # Path to the an shell script that adds install_dir to PATH
    local _env_script_path
    # Potentially-late-bound version of install_dir to write env_script
    local _install_dir_expr
    # Potentially-late-bound version of env_script_path to write to rcfiles like $HOME/.profile
    local _env_script_path_expr
    # Forces the install to occur at this path, not the default
    local _force_install_dir
    # Which install layout to use - "flat" or "hierarchical"
    local _install_layout="unspecified"
    # A list of binaries which are shadowed in the PATH
    local _shadowed_bins=""

    # Check the newer app-specific variable before falling back
    # to the older generic one
    if [ -n "${UV_INSTALL_DIR:-}" ]; then
        _force_install_dir="$UV_INSTALL_DIR"
        _install_layout="flat"
    elif [ -n "${CARGO_DIST_FORCE_INSTALL_DIR:-}" ]; then
        _force_install_dir="$CARGO_DIST_FORCE_INSTALL_DIR"
        _install_layout="flat"
    elif [ -n "$UNMANAGED_INSTALL" ]; then
        _force_install_dir="$UNMANAGED_INSTALL"
        _install_layout="flat"
    fi

    # Check if the install layout should be changed from `flat` to `cargo-home`
    # for backwards compatible updates of applications that switched layouts.
    if [ -n "${_force_install_dir:-}" ]; then
        if [ "$_install_layout" = "flat" ]; then
            # If the install directory is targeting the Cargo home directory, then
            # we assume this application was previously installed that layout
            if [ "$_force_install_dir" = "${CARGO_HOME:-${INFERRED_HOME:-}/.cargo}" ]; then
                _install_layout="cargo-home"
            fi
        fi
     fi

    # Before actually consulting the configured install strategy, see
    # if we're overriding it.
    if [ -n "${_force_install_dir:-}" ]; then
        case "$_install_layout" in
            "hierarchical")
                _install_dir="$_force_install_dir/bin"
                _lib_install_dir="$_force_install_dir/lib"
                _receipt_install_dir="$_force_install_dir"
                _env_script_path="$_force_install_dir/env"
                _install_dir_expr="$(replace_home "$_force_install_dir/bin")"
                _env_script_path_expr="$(replace_home "$_force_install_dir/env")"
                ;;
            "cargo-home")
                _install_dir="$_force_install_dir/bin"
                _lib_install_dir="$_force_install_dir/bin"
                _receipt_install_dir="$_force_install_dir"
                _env_script_path="$_force_install_dir/env"
                _install_dir_expr="$(replace_home "$_force_install_dir/bin")"
                _env_script_path_expr="$(replace_home "$_force_install_dir/env")"
                ;;
            "flat")
                _install_dir="$_force_install_dir"
                _lib_install_dir="$_force_install_dir"
                _receipt_install_dir="$_install_dir"
                _env_script_path="$_force_install_dir/env"
                _install_dir_expr="$(replace_home "$_force_install_dir")"
                _env_script_path_expr="$(replace_home "$_force_install_dir/env")"
                ;;
            *)
                err "Unrecognized install layout: $_install_layout"
                ;;
        esac
    fi
    if [ -z "${_install_dir:-}" ]; then
        _install_layout="flat"
        # Install to $XDG_BIN_HOME
        if [ -n "${XDG_BIN_HOME:-}" ]; then
            _install_dir="$XDG_BIN_HOME"
            _lib_install_dir="$_install_dir"
            _receipt_install_dir="$_install_dir"
            _env_script_path="$XDG_BIN_HOME/env"
            _install_dir_expr="$(replace_home "$_install_dir")"
            _env_script_path_expr="$(replace_home "$_env_script_path")"
        fi
    fi
    if [ -z "${_install_dir:-}" ]; then
        _install_layout="flat"
        # Install to $XDG_DATA_HOME/../bin
        if [ -n "${XDG_DATA_HOME:-}" ]; then
            _install_dir="$XDG_DATA_HOME/../bin"
            _lib_install_dir="$_install_dir"
            _receipt_install_dir="$_install_dir"
            _env_script_path="$XDG_DATA_HOME/../bin/env"
            _install_dir_expr="$(replace_home "$_install_dir")"
            _env_script_path_expr="$(replace_home "$_env_script_path")"
        fi
    fi
    if [ -z "${_install_dir:-}" ]; then
        _install_layout="flat"
        # Install to $HOME/.local/bin
        if [ -n "${INFERRED_HOME:-}" ]; then
            _install_dir="$INFERRED_HOME/.local/bin"
            _lib_install_dir="$INFERRED_HOME/.local/bin"
            _receipt_install_dir="$_install_dir"
            _env_script_path="$INFERRED_HOME/.local/bin/env"
            _install_dir_expr="$INFERRED_HOME_EXPRESSION/.local/bin"
            _env_script_path_expr="$INFERRED_HOME_EXPRESSION/.local/bin/env"
        fi
    fi

    if [ -z "$_install_dir_expr" ]; then
        err "could not find a valid path to install to!"
    fi

    # Identical to the sh version, just with a .fish file extension
    # We place it down here to wait until it's been assigned in every
    # path.
    _fish_env_script_path="${_env_script_path}.fish"
    _fish_env_script_path_expr="${_env_script_path_expr}.fish"

    # Replace the temporary cargo home with the calculated one
    RECEIPT=$(echo "$RECEIPT" | sed "s,AXO_INSTALL_PREFIX,$_receipt_install_dir,")
    # Also replace the aliases with the arch-specific one
    RECEIPT=$(echo "$RECEIPT" | sed "s'\"binary_aliases\":{}'\"binary_aliases\":$(json_binary_aliases "$_arch")'")
    # And replace the install layout
    RECEIPT=$(echo "$RECEIPT" | sed "s'\"install_layout\":\"unspecified\"'\"install_layout\":\"$_install_layout\"'")
    if [ "$NO_MODIFY_PATH" = "1" ]; then
        RECEIPT=$(echo "$RECEIPT" | sed "s'\"modify_path\":true'\"modify_path\":false'")
    fi

    say "installing to $_install_dir"
    ensure mkdir -p "$_install_dir"
    ensure mkdir -p "$_lib_install_dir"

    # copy all the binaries to the install dir
    local _src_dir="$1"
    local _bins="$2"
    local _libs="$3"
    local _staticlibs="$4"
    local _arch="$5"
    for _bin_name in $_bins; do
        local _bin="$_src_dir/$_bin_name"
        ensure mv "$_bin" "$_install_dir"
        # unzip seems to need this chmod
        ensure chmod +x "$_install_dir/$_bin_name"
        for _dest in $(aliases_for_binary "$_bin_name" "$_arch"); do
            ln -sf "$_install_dir/$_bin_name" "$_install_dir/$_dest"
        done
        say "  $_bin_name"
    done
    # Like the above, but no aliases
    for _lib_name in $_libs; do
        local _lib="$_src_dir/$_lib_name"
        ensure mv "$_lib" "$_lib_install_dir"
        # unzip seems to need this chmod
        ensure chmod +x "$_lib_install_dir/$_lib_name"
        say "  $_lib_name"
    done
    for _lib_name in $_staticlibs; do
        local _lib="$_src_dir/$_lib_name"
        ensure mv "$_lib" "$_lib_install_dir"
        # unzip seems to need this chmod
        ensure chmod +x "$_lib_install_dir/$_lib_name"
        say "  $_lib_name"
    done

    say "everything's installed!"

    # Avoid modifying the users PATH if they are managing their PATH manually
    case :$PATH:
      in *:$_install_dir:*) NO_MODIFY_PATH=1 ;;
         *) ;;
    esac

    if [ "0" = "$NO_MODIFY_PATH" ]; then
        add_install_dir_to_ci_path "$_install_dir"
        add_install_dir_to_path "$_install_dir_expr" "$_env_script_path" "$_env_script_path_expr" ".profile" "sh"
        exit1=$?
        shotgun_install_dir_to_path "$_install_dir_expr" "$_env_script_path" "$_env_script_path_expr" ".profile .bashrc .bash_profile .bash_login" "sh"
        exit2=$?
        add_install_dir_to_path "$_install_dir_expr" "$_env_script_path" "$_env_script_path_expr" ".zshrc .zshenv" "sh"
        exit3=$?
        # This path may not exist by default
        ensure mkdir -p "$INFERRED_HOME/.config/fish/conf.d"
        exit4=$?
        add_install_dir_to_path "$_install_dir_expr" "$_fish_env_script_path" "$_fish_env_script_path_expr" ".config/fish/conf.d/$APP_NAME.env.fish" "fish"
        exit5=$?

        if [ "${exit1:-0}" = 1 ] || [ "${exit2:-0}" = 1 ] || [ "${exit3:-0}" = 1 ] || [ "${exit4:-0}" = 1 ] || [ "${exit5:-0}" = 1 ]; then
            say ""
            say "To add $_install_dir_expr to your PATH, either restart your shell or run:"
            say ""
            say "    source $_env_script_path_expr (sh, bash, zsh)"
            say "    source $_fish_env_script_path_expr (fish)"
        fi
    fi

    _shadowed_bins="$(check_for_shadowed_bins "$_install_dir" "$_bins")"
    if [ -n "$_shadowed_bins" ]; then
        warn "The following commands are shadowed by other commands in your PATH:$_shadowed_bins"
    fi
}

check_for_shadowed_bins() {
    local _install_dir="$1"
    local _bins="$2"
    local _shadow

    for _bin_name in $_bins; do
        _shadow="$(command -v "$_bin_name")"
        if [ -n "$_shadow" ] && [ "$_shadow" != "$_install_dir/$_bin_name" ]; then
            _shadowed_bins="$_shadowed_bins $_bin_name"
        fi
    done

    echo "$_shadowed_bins"
}

print_home_for_script() {
    local script="$1"

    local _home
    case "$script" in
        # zsh has a special ZDOTDIR directory, which if set
        # should be considered instead of $HOME
        .zsh*)
            if [ -n "${ZDOTDIR:-}" ]; then
                _home="$ZDOTDIR"
            else
                _home="$INFERRED_HOME"
            fi
            ;;
        *)
            _home="$INFERRED_HOME"
            ;;
    esac

    echo "$_home"
}

add_install_dir_to_ci_path() {
    # Attempt to do CI-specific rituals to get the install-dir on PATH faster
    local _install_dir="$1"

    # If GITHUB_PATH is present, then write install_dir to the file it refs.
    # After each GitHub Action, the contents will be added to PATH.
    # So if you put a curl | sh for this script in its own "run" step,
    # the next step will have this dir on PATH.
    #
    # Note that GITHUB_PATH will not resolve any variables, so we in fact
    # want to write install_dir and not install_dir_expr
    if [ -n "${GITHUB_PATH:-}" ]; then
        ensure echo "$_install_dir" >> "$GITHUB_PATH"
    fi
}

add_install_dir_to_path() {
    # Edit rcfiles ($HOME/.profile) to add install_dir to $PATH
    #
    # We do this slightly indirectly by creating an "env" shell script which checks if install_dir
    # is on $PATH already, and prepends it if not. The actual line we then add to rcfiles
    # is to just source that script. This allows us to blast it into lots of different rcfiles and
    # have it run multiple times without causing problems. It's also specifically compatible
    # with the system rustup uses, so that we don't conflict with it.
    local _install_dir_expr="$1"
    local _env_script_path="$2"
    local _env_script_path_expr="$3"
    local _rcfiles="$4"
    local _shell="$5"

    if [ -n "${INFERRED_HOME:-}" ]; then
        local _target
        local _home

        # Find the first file in the array that exists and choose
        # that as our target to write to
        for _rcfile_relative in $_rcfiles; do
            _home="$(print_home_for_script "$_rcfile_relative")"
            local _rcfile="$_home/$_rcfile_relative"

            if [ -f "$_rcfile" ]; then
                _target="$_rcfile"
                break
            fi
        done

        # If we didn't find anything, pick the first entry in the
        # list as the default to create and write to
        if [ -z "${_target:-}" ]; then
            local _rcfile_relative
            _rcfile_relative="$(echo "$_rcfiles" | awk '{ print $1 }')"
            _home="$(print_home_for_script "$_rcfile_relative")"
            _target="$_home/$_rcfile_relative"
        fi

        # `source x` is an alias for `. x`, and the latter is more portable/actually-posix.
        # This apparently comes up a lot on freebsd. It's easy enough to always add
        # the more robust line to rcfiles, but when telling the user to apply the change
        # to their current shell ". x" is pretty easy to misread/miscopy, so we use the
        # prettier "source x" line there. Hopefully people with Weird Shells are aware
        # this is a thing and know to tweak it (or just restart their shell).
        local _robust_line=". \"$_env_script_path_expr\""
        local _pretty_line="source \"$_env_script_path_expr\""

        # Add the env script if it doesn't already exist
        if [ ! -f "$_env_script_path" ]; then
            say_verbose "creating $_env_script_path"
            if [ "$_shell" = "sh" ]; then
                write_env_script_sh "$_install_dir_expr" "$_env_script_path"
            else
                write_env_script_fish "$_install_dir_expr" "$_env_script_path"
            fi
        else
            say_verbose "$_env_script_path already exists"
        fi

        # Check if the line is already in the rcfile
        # grep: 0 if matched, 1 if no match, and 2 if an error occurred
        #
        # Ideally we could use quiet grep (-q), but that makes "match" and "error"
        # have the same behaviour, when we want "no match" and "error" to be the same
        # (on error we want to create the file, which >> conveniently does)
        #
        # We search for both kinds of line here just to do the right thing in more cases.
        if ! grep -F "$_robust_line" "$_target" > /dev/null 2>/dev/null && \
           ! grep -F "$_pretty_line" "$_target" > /dev/null 2>/dev/null
        then
            # If the script now exists, add the line to source it to the rcfile
            # (This will also create the rcfile if it doesn't exist)
            if [ -f "$_env_script_path" ]; then
                local _line
                # Fish has deprecated `.` as an alias for `source` and
                # it will be removed in a later version.
                # https://fishshell.com/docs/current/cmds/source.html
                # By contrast, `.` is the traditional syntax in sh and
                # `source` isn't always supported in all circumstances.
                if [ "$_shell" = "fish" ]; then
                    _line="$_pretty_line"
                else
                    _line="$_robust_line"
                fi
                say_verbose "adding $_line to $_target"
                # prepend an extra newline in case the user's file is missing a trailing one
                ensure echo "" >> "$_target"
                ensure echo "$_line" >> "$_target"
                return 1
            fi
        else
            say_verbose "$_install_dir already on PATH"
        fi
    fi
}

shotgun_install_dir_to_path() {
    # Edit rcfiles ($HOME/.profile) to add install_dir to $PATH
    # (Shotgun edition - write to all provided files that exist rather than just the first)
    local _install_dir_expr="$1"
    local _env_script_path="$2"
    local _env_script_path_expr="$3"
    local _rcfiles="$4"
    local _shell="$5"

    if [ -n "${INFERRED_HOME:-}" ]; then
        local _found=false
        local _home

        for _rcfile_relative in $_rcfiles; do
            _home="$(print_home_for_script "$_rcfile_relative")"
            local _rcfile_abs="$_home/$_rcfile_relative"

            if [ -f "$_rcfile_abs" ]; then
                _found=true
                add_install_dir_to_path "$_install_dir_expr" "$_env_script_path" "$_env_script_path_expr" "$_rcfile_relative" "$_shell"
            fi
        done

        # Fall through to previous "create + write to first file in list" behavior
	    if [ "$_found" = false ]; then
            add_install_dir_to_path "$_install_dir_expr" "$_env_script_path" "$_env_script_path_expr" "$_rcfiles" "$_shell"
        fi
    fi
}

write_env_script_sh() {
    # write this env script to the given path (this cat/EOF stuff is a "heredoc" string)
    local _install_dir_expr="$1"
    local _env_script_path="$2"
    ensure cat <<EOF > "$_env_script_path"
#!/bin/sh
# add binaries to PATH if they aren't added yet
# affix colons on either side of \$PATH to simplify matching
case ":\${PATH}:" in
    *:"$_install_dir_expr":*)
        ;;
    *)
        # Prepending path in case a system-installed binary needs to be overridden
        export PATH="$_install_dir_expr:\$PATH"
        ;;
esac
EOF
}

write_env_script_fish() {
    # write this env script to the given path (this cat/EOF stuff is a "heredoc" string)
    local _install_dir_expr="$1"
    local _env_script_path="$2"
    ensure cat <<EOF > "$_env_script_path"
if not contains "$_install_dir_expr" \$PATH
    # Prepending path in case a system-installed binary needs to be overridden
    set -x PATH "$_install_dir_expr" \$PATH
end
EOF
}

get_current_exe() {
    # Returns the executable used for system architecture detection
    # This is only run on Linux
    local _current_exe
    if test -L /proc/self/exe ; then
        _current_exe=/proc/self/exe
    else
        warn "Unable to find /proc/self/exe. System architecture detection might be inaccurate."
        if test -n "$SHELL" ; then
            _current_exe=$SHELL
        else
            need_cmd /bin/sh
            _current_exe=/bin/sh
        fi
        warn "Falling back to $_current_exe."
    fi
    echo "$_current_exe"
}

get_bitness() {
    need_cmd head
    # Architecture detection without dependencies beyond coreutils.
    # ELF files start out "\x7fELF", and the following byte is
    #   0x01 for 32-bit and
    #   0x02 for 64-bit.
    # The printf builtin on some shells like dash only supports octal
    # escape sequences, so we use those.
    local _current_exe=$1
    local _current_exe_head
    _current_exe_head=$(head -c 5 "$_current_exe")
    if [ "$_current_exe_head" = "$(printf '\177ELF\001')" ]; then
        echo 32
    elif [ "$_current_exe_head" = "$(printf '\177ELF\002')" ]; then
        echo 64
    else
        err "unknown platform bitness"
    fi
}

is_host_amd64_elf() {
    local _current_exe=$1

    need_cmd head
    need_cmd tail
    # ELF e_machine detection without dependencies beyond coreutils.
    # Two-byte field at offset 0x12 indicates the CPU,
    # but we're interested in it being 0x3E to indicate amd64, or not that.
    local _current_exe_machine
    _current_exe_machine=$(head -c 19 "$_current_exe" | tail -c 1)
    [ "$_current_exe_machine" = "$(printf '\076')" ]
}

get_endianness() {
    local _current_exe=$1
    local cputype=$2
    local suffix_eb=$3
    local suffix_el=$4

    # detect endianness without od/hexdump, like get_bitness() does.
    need_cmd head
    need_cmd tail

    local _current_exe_endianness
    _current_exe_endianness="$(head -c 6 "$_current_exe" | tail -c 1)"
    if [ "$_current_exe_endianness" = "$(printf '\001')" ]; then
        echo "${cputype}${suffix_el}"
    elif [ "$_current_exe_endianness" = "$(printf '\002')" ]; then
        echo "${cputype}${suffix_eb}"
    else
        err "unknown platform endianness"
    fi
}

# Detect the Linux/LoongArch UAPI flavor, with all errors being non-fatal.
# Returns 0 or 234 in case of successful detection, 1 otherwise (/tmp being
# noexec, or other causes).
check_loongarch_uapi() {
    need_cmd base64

    local _tmp
    if ! _tmp="$(ensure mktemp)"; then
        return 1
    fi

    # Minimal Linux/LoongArch UAPI detection, exiting with 0 in case of
    # upstream ("new world") UAPI, and 234 (-EINVAL truncated) in case of
    # old-world (as deployed on several early commercial Linux distributions
    # for LoongArch).
    #
    # See https://gist.github.com/xen0n/5ee04aaa6cecc5c7794b9a0c3b65fc7f for
    # source to this helper binary.
    ignore base64 -d > "$_tmp" <<EOF
f0VMRgIBAQAAAAAAAAAAAAIAAgEBAAAAeAAgAAAAAABAAAAAAAAAAAAAAAAAAAAAQQAAAEAAOAAB
AAAAAAAAAAEAAAAFAAAAAAAAAAAAAAAAACAAAAAAAAAAIAAAAAAAJAAAAAAAAAAkAAAAAAAAAAAA
AQAAAAAABCiAAwUAFQAGABUAByCAAwsYggMAACsAC3iBAwAAKwAxen0n
EOF

    ignore chmod u+x "$_tmp"
    if [ ! -x "$_tmp" ]; then
        ignore rm "$_tmp"
        return 1
    fi

    "$_tmp"
    local _retval=$?

    ignore rm "$_tmp"
    return "$_retval"
}

ensure_loongarch_uapi() {
    check_loongarch_uapi
    case $? in
        0)
            return 0
            ;;
        234)
            err 'Your Linux kernel does not provide the ABI required by this distribution.'
            ;;
        *)
            warn "Cannot determine current system's ABI flavor, continuing anyway."
            warn 'Note that the official distribution only works with the upstream kernel ABI.'
            warn 'Installation will fail if your running kernel happens to be incompatible.'
            ;;
    esac
}

get_architecture() {
    local _ostype
    local _cputype
    _ostype="$(uname -s)"
    _cputype="$(uname -m)"
    local _clibtype="gnu"
    local _local_glibc

    if [ "$_ostype" = Linux ]; then
        if [ "$(uname -o)" = Android ]; then
            _ostype=Android
        fi
        if ldd --version 2>&1 | grep -q 'musl'; then
            _clibtype="musl-dynamic"
        else
            # Assume all other linuxes are glibc (even if wrong, static libc fallback will apply)
            _clibtype="gnu"
        fi
    fi

    if [ "$_ostype" = Darwin ]; then
        # Darwin `uname -m` can lie due to Rosetta shenanigans. If you manage to
        # invoke a native shell binary and then a native uname binary, you can
        # get the real answer, but that's hard to ensure, so instead we use
        # `sysctl` (which doesn't lie) to check for the actual architecture.
        if [ "$_cputype" = i386 ]; then
            # Handling i386 compatibility mode in older macOS versions (<10.15)
            # running on x86_64-based Macs.
            # Starting from 10.15, macOS explicitly bans all i386 binaries from running.
            # See: <https://support.apple.com/en-us/HT208436>

            # Avoid `sysctl: unknown oid` stderr output and/or non-zero exit code.
            if sysctl hw.optional.x86_64 2> /dev/null || true | grep -q ': 1'; then
                _cputype=x86_64
            fi
        elif [ "$_cputype" = x86_64 ]; then
            # Handling x86-64 compatibility mode (a.k.a. Rosetta 2)
            # in newer macOS versions (>=11) running on arm64-based Macs.
            # Rosetta 2 is built exclusively for x86-64 and cannot run i386 binaries.

            # Avoid `sysctl: unknown oid` stderr output and/or non-zero exit code.
            if sysctl hw.optional.arm64 2> /dev/null || true | grep -q ': 1'; then
                _cputype=arm64
            fi
        fi
    fi

    if [ "$_ostype" = SunOS ]; then
        # Both Solaris and illumos presently announce as "SunOS" in "uname -s"
        # so use "uname -o" to disambiguate.  We use the full path to the
        # system uname in case the user has coreutils uname first in PATH,
        # which has historically sometimes printed the wrong value here.
        if [ "$(/usr/bin/uname -o)" = illumos ]; then
            _ostype=illumos
        fi

        # illumos systems have multi-arch userlands, and "uname -m" reports the
        # machine hardware name; e.g., "i86pc" on both 32- and 64-bit x86
        # systems.  Check for the native (widest) instruction set on the
        # running kernel:
        if [ "$_cputype" = i86pc ]; then
            _cputype="$(isainfo -n)"
        fi
    fi

    local _current_exe
    case "$_ostype" in

        Android)
            _ostype=linux-android
            ;;

        Linux)
            _current_exe=$(get_current_exe)
            _ostype=unknown-linux-$_clibtype
            _bitness=$(get_bitness "$_current_exe")
            ;;

        FreeBSD)
            _ostype=unknown-freebsd
            ;;

        NetBSD)
            _ostype=unknown-netbsd
            ;;

        DragonFly)
            _ostype=unknown-dragonfly
            ;;

        Darwin)
            _ostype=apple-darwin
            ;;

        illumos)
            _ostype=unknown-illumos
            ;;

        MINGW* | MSYS* | CYGWIN* | Windows_NT)
            _ostype=pc-windows-gnu
            ;;

        *)
            err "unrecognized OS type: $_ostype"
            ;;

    esac

    case "$_cputype" in

        i386 | i486 | i686 | i786 | x86)
            _cputype=i686
            ;;

        xscale | arm)
            _cputype=arm
            if [ "$_ostype" = "linux-android" ]; then
                _ostype=linux-androideabi
            fi
            ;;

        armv6l)
            _cputype=arm
            if [ "$_ostype" = "linux-android" ]; then
                _ostype=linux-androideabi
            else
                _ostype="${_ostype}eabihf"
            fi
            ;;

        armv7l | armv8l)
            _cputype=armv7
            if [ "$_ostype" = "linux-android" ]; then
                _ostype=linux-androideabi
            else
                _ostype="${_ostype}eabihf"
            fi
            ;;

        aarch64 | arm64)
            _cputype=aarch64
            ;;

        x86_64 | x86-64 | x64 | amd64)
            _cputype=x86_64
            ;;

        mips)
            _cputype=$(get_endianness "$_current_exe" mips '' el)
            ;;

        mips64)
            if [ "$_bitness" -eq 64 ]; then
                # only n64 ABI is supported for now
                _ostype="${_ostype}abi64"
                _cputype=$(get_endianness "$_current_exe" mips64 '' el)
            fi
            ;;

        ppc)
            _cputype=powerpc
            ;;

        ppc64)
            _cputype=powerpc64
            ;;

        ppc64le)
            _cputype=powerpc64le
            ;;

        s390x)
            _cputype=s390x
            ;;
        riscv64)
            _cputype=riscv64gc
            ;;
        loongarch64)
            _cputype=loongarch64
            ensure_loongarch_uapi
            ;;
        *)
            err "unknown CPU type: $_cputype"

    esac

    # Detect 64-bit linux with 32-bit userland
    if [ "${_ostype}" = unknown-linux-gnu ] && [ "${_bitness}" -eq 32 ]; then
        case $_cputype in
            x86_64)
                # 32-bit executable for amd64 = x32
                if is_host_amd64_elf "$_current_exe"; then {
                    err "x32 linux unsupported"
                }; else
                    _cputype=i686
                fi
                ;;
            mips64)
                _cputype=$(get_endianness "$_current_exe" mips '' el)
                ;;
            powerpc64)
                _cputype=powerpc
                ;;
            aarch64)
                _cputype=armv7
                if [ "$_ostype" = "linux-android" ]; then
                    _ostype=linux-androideabi
                else
                    _ostype="${_ostype}eabihf"
                fi
                ;;
            riscv64gc)
                err "riscv64 with 32-bit userland unsupported"
                ;;
        esac
    fi

    # Detect armv7 but without the CPU features Rust needs in that build,
    # and fall back to arm.
    if [ "$_ostype" = "unknown-linux-gnueabihf" ] && [ "$_cputype" = armv7 ]; then
        if ! (ensure grep '^Features' /proc/cpuinfo | grep -E -q 'neon|simd') ; then
            # Either `/proc/cpuinfo` is malformed or unavailable, or
            # at least one processor does not have NEON (which is asimd on armv8+).
            _cputype=arm
        fi
    fi

    _arch="${_cputype}-${_ostype}"

    RETVAL="$_arch"
}

say() {
    if [ "0" = "$PRINT_QUIET" ]; then
        echo "$1"
    fi
}

say_verbose() {
    if [ "1" = "$PRINT_VERBOSE" ]; then
        echo "$1"
    fi
}

warn() {
    if [ "0" = "$PRINT_QUIET" ]; then
        local red
        local reset
        red=$(tput setaf 1 2>/dev/null || echo '')
        reset=$(tput sgr0 2>/dev/null || echo '')
        say "${red}WARN${reset}: $1" >&2
    fi
}

err() {
    if [ "0" = "$PRINT_QUIET" ]; then
        local red
        local reset
        red=$(tput setaf 1 2>/dev/null || echo '')
        reset=$(tput sgr0 2>/dev/null || echo '')
        say "${red}ERROR${reset}: $1" >&2
    fi
    exit 1
}

need_cmd() {
    if ! check_cmd "$1"
    then err "need '$1' (command not found)"
    fi
}

check_cmd() {
    command -v "$1" > /dev/null 2>&1
    return $?
}

assert_nz() {
    if [ -z "$1" ]; then err "assert_nz $2"; fi
}

# Run a command that should never fail. If the command fails execution
# will immediately terminate with an error showing the failing
# command.
ensure() {
    if ! "$@"; then err "command failed: $*"; fi
}

# This is just for indicating that commands' results are being
# intentionally ignored. Usually, because it's being executed
# as part of error handling.
ignore() {
    "$@"
}

# This wraps curl or wget. Try curl first, if not installed,
# use wget instead.
downloader() {
    # Check if we have a broken snap curl
    # https://github.com/boukendesho/curl-snap/issues/1
    _snap_curl=0
    if command -v curl > /dev/null 2>&1; then
      _curl_path=$(command -v curl)
      if echo "$_curl_path" | grep "/snap/" > /dev/null 2>&1; then
        _snap_curl=1
      fi
    fi

    # Check if we have a working (non-snap) curl
    if check_cmd curl && [ "$_snap_curl" = "0" ]
    then _dld=curl
    # Try wget for both no curl and the broken snap curl
    elif check_cmd wget
    then _dld=wget
    # If we can't fall back from broken snap curl to wget, report the broken snap curl
    elif [ "$_snap_curl" = "1" ]
    then
      say "curl installed with snap cannot be used to install $APP_NAME"
      say "due to missing permissions. Please uninstall it and"
      say "reinstall curl with a different package manager (e.g., apt)."
      say "See https://github.com/boukendesho/curl-snap/issues/1"
      exit 1
    else _dld='curl or wget' # to be used in error message of need_cmd
    fi

    if [ "$1" = --check ]
    then need_cmd "$_dld"
    elif [ "$_dld" = curl ]; then
        if [ -n "${AUTH_TOKEN:-}" ]; then
            curl -sSfL --header "Authorization: Bearer ${AUTH_TOKEN}" "$1" -o "$2"
        else
            curl -sSfL "$1" -o "$2"
        fi
    elif [ "$_dld" = wget ]; then
        if [ -n "${AUTH_TOKEN:-}" ]; then
            wget --header "Authorization: Bearer ${AUTH_TOKEN}" "$1" -O "$2"
        else
            wget "$1" -O "$2"
        fi
    else err "Unknown downloader"   # should not reach here
    fi
}

verify_checksum() {
    local _file="$1"
    local _checksum_style="$2"
    local _checksum_value="$3"
    local _calculated_checksum

    if [ -z "$_checksum_value" ]; then
        return 0
    fi
    case "$_checksum_style" in
        sha256)
            if ! check_cmd sha256sum; then
                say "skipping sha256 checksum verification (it requires the 'sha256sum' command)"
                return 0
            fi
            _calculated_checksum="$(sha256sum -b "$_file" | awk '{printf $1}')"
            ;;
        sha512)
            if ! check_cmd sha512sum; then
                say "skipping sha512 checksum verification (it requires the 'sha512sum' command)"
                return 0
            fi
            _calculated_checksum="$(sha512sum -b "$_file" | awk '{printf $1}')"
            ;;
        sha3-256)
            if ! check_cmd openssl; then
                say "skipping sha3-256 checksum verification (it requires the 'openssl' command)"
                return 0
            fi
            _calculated_checksum="$(openssl dgst -sha3-256 "$_file" | awk '{printf $NF}')"
            ;;
        sha3-512)
            if ! check_cmd openssl; then
                say "skipping sha3-512 checksum verification (it requires the 'openssl' command)"
                return 0
            fi
            _calculated_checksum="$(openssl dgst -sha3-512 "$_file" | awk '{printf $NF}')"
            ;;
        blake2s)
            if ! check_cmd b2sum; then
                say "skipping blake2s checksum verification (it requires the 'b2sum' command)"
                return 0
            fi
            # Test if we have official b2sum with blake2s support
            local _well_known_blake2s_checksum="93314a61f470985a40f8da62df10ba0546dc5216e1d45847bf1dbaa42a0e97af"
            local _test_blake2s
            _test_blake2s="$(printf "can do blake2s" | b2sum -a blake2s | awk '{printf $1}')" || _test_blake2s=""

            if [ "X$_test_blake2s" = "X$_well_known_blake2s_checksum" ]; then
                _calculated_checksum="$(b2sum -a blake2s "$_file" | awk '{printf $1}')" || _calculated_checksum=""
            else
                say "skipping blake2s checksum verification (installed b2sum doesn't support blake2s)"
                return 0
            fi
            ;;
        blake2b)
            if ! check_cmd b2sum; then
                say "skipping blake2b checksum verification (it requires the 'b2sum' command)"
                return 0
            fi
            _calculated_checksum="$(b2sum "$_file" | awk '{printf $1}')"
            ;;
        false)
            ;;
        *)
            say "skipping unknown checksum style: $_checksum_style"
            return 0
            ;;
    esac

    if [ "$_calculated_checksum" != "$_checksum_value" ]; then
        err "checksum mismatch
            want: $_checksum_value
            got:  $_calculated_checksum"
    fi
}

download_binary_and_run_installer "$@" || exit 1
