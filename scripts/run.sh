#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/run.sh

Installs the app if needed, downloads the models, measures the speed of this
computer the first time, and starts the app. It takes no options. Steps that
are already done are skipped.

On macOS, it first checks for Python 3.12, git, ffmpeg and BlackHole 2ch. If
something is missing, it asks one question and installs it with Homebrew.
USAGE
}

if [ "$#" -gt 0 ]; then
  case "$1" in
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
fi

cd "$(dirname "${BASH_SOURCE[0]}")/.."

hash_file() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | cut -d ' ' -f 1
  else
    sha256sum "$1" | cut -d ' ' -f 1
  fi
}

blackhole_driver="/Library/Audio/Plug-Ins/HAL/BlackHole2ch.driver"
brew_paths="/opt/homebrew/bin/brew /usr/local/bin/brew"

is_macos() {
  [ "$(uname -s)" = "Darwin" ]
}

git_works() {
  git --version >/dev/null 2>&1
}

prerequisites="python git ffmpeg blackhole"

say_ok() {
  echo "  ✓ $1"
}

say_missing() {
  echo "  ✗ $1"
}

say_fail() {
  echo "  ✗ $1" >&2
}

item_name() {
  case "$1" in
    python) echo "Python 3.12" ;;
    blackhole) echo "BlackHole 2ch" ;;
    *) echo "$1" ;;
  esac
}

is_present() {
  case "$1" in
    python) command -v python3.12 >/dev/null 2>&1 ;;
    git) git_works ;;
    ffmpeg) command -v ffmpeg >/dev/null 2>&1 ;;
    blackhole) [ -d "$blackhole_driver" ] ;;
  esac
}

find_missing() {
  local missing="" item
  for item in $prerequisites; do
    is_present "$item" || missing="$missing $item"
  done
  echo "${missing# }"
}

describe_missing() {
  local names="" item
  for item in $1; do
    names="$names, $(item_name "$item")"
  done
  echo "${names#, }"
}

was_reported() {
  case " $reported_missing " in
    *" $1 "*) return 0 ;;
  esac
  return 1
}

ask_yes_no() {
  local answer
  if [ ! -t 0 ]; then
    echo "There is no terminal to answer, so the answer is Yes."
    return 0
  fi
  while true; do
    printf 'Some things are missing. Install them now? [Y/n] '
    read -r answer || return 0
    answer="$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')"
    case "$answer" in
      "" | y | yes) return 0 ;;
      n | no) return 1 ;;
    esac
  done
}

load_brew() {
  local brew_path
  for brew_path in $brew_paths; do
    if [ -x "$brew_path" ]; then
      eval "$("$brew_path" shellenv)"
      return 0
    fi
  done
  return 1
}

ensure_brew() {
  command -v brew >/dev/null 2>&1 && return 0
  load_brew && return 0
  echo "Installing Homebrew (your Mac may ask for your password)..."
  if /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" && load_brew && command -v brew >/dev/null 2>&1; then
    say_ok "Homebrew installed"
    return 0
  fi
  say_fail "Homebrew could not be installed. Install it from https://brew.sh and run this script again."
  exit 1
}

install_item() {
  local item="$1" name
  local -a command_line
  name="$(item_name "$item")"
  case "$item" in
    python) command_line=(brew install python@3.12) ;;
    blackhole) command_line=(brew install --cask blackhole-2ch) ;;
    *) command_line=(brew install "$item") ;;
  esac
  if [ "$item" = "blackhole" ]; then
    echo "Installing $name (your Mac may ask for your password)..."
  else
    echo "Installing $name..."
  fi
  if "${command_line[@]}"; then
    say_ok "$name installed"
    if [ "$item" = "blackhole" ]; then
      sudo killall coreaudiod || true
      echo "  Tip: if $name does not show up in your apps, restart your Mac."
    fi
    return 0
  fi
  say_fail "$name could not be installed. You can try later with: ${command_line[*]}"
  [ "$item" != "python" ] || exit 1
}

install_missing() {
  local item
  ensure_brew
  for item in $1; do
    install_item "$item"
  done
}

reported_missing=""

install_prerequisites() {
  local missing item
  is_macos || return 0
  missing="$(find_missing)"
  if [ -z "$missing" ]; then
    echo "✓ Everything voice-clone needs is ready."
    return 0
  fi
  echo "Checking what voice-clone needs..."
  for item in $prerequisites; do
    if is_present "$item"; then
      say_ok "$(item_name "$item") is already installed"
    else
      say_missing "$(item_name "$item") is missing"
    fi
  done
  echo
  if ask_yes_no; then
    echo
    install_missing "$missing"
  fi
  reported_missing="$(find_missing)"
  echo
  if [ -z "$reported_missing" ]; then
    echo "✓ Everything voice-clone needs is ready."
  else
    echo "Still missing: $(describe_missing "$reported_missing"). The app may not work fully until they are installed."
  fi
}

install_prerequisites

if ! command -v python3.12 >/dev/null 2>&1; then
  echo "Python 3.12 was not found." >&2
  echo "Install it with: brew install python@3.12" >&2
  exit 1
fi

venv_python=".venv/bin/python"
stamp=".venv/.voice-clone-install"

if [ -e ".venv" ]; then
  venv_version=""
  if [ -x "$venv_python" ]; then
    venv_version="$("$venv_python" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true)"
  fi
  if [ "$venv_version" != "3.12" ]; then
    echo "The .venv folder was not made with Python 3.12 (found: ${venv_version:-unknown}). Making it again."
    rm -rf .venv
  fi
fi
if [ ! -e ".venv" ]; then
  echo "Making .venv with Python 3.12."
  python3.12 -m venv .venv
fi

installed=0
current_hash="$(hash_file pyproject.toml)"
stamp_text="dev:$current_hash"
if [ ! -f "$stamp" ] || [ "$(cat "$stamp")" != "$stamp_text" ]; then
  installed=1
  echo "Installing the app. This can take a few minutes."
  if ! "$venv_python" -m pip install pip-system-certs; then
    echo "Could not install pip-system-certs. If you are behind a company proxy, check that HTTPS_PROXY is set and the company certificate is installed in the system." >&2
    exit 1
  fi
  "$venv_python" -m pip install --upgrade pip
  "$venv_python" -m pip install -e ".[dev]"
  echo "$stamp_text" >"$stamp"
fi

if ! "$venv_python" -m voice_clone download-models; then
  echo "Warning: the base models were not downloaded. They will be tried again next time." >&2
fi

if ! git_works; then
  echo "Warning: Applio was skipped because git is not installed. Install it with: xcode-select --install" >&2
elif ! "$venv_python" -m voice_clone install-applio; then
  echo "Warning: Applio was not installed. It will be tried again next time." >&2
fi

speed_status=0
"$venv_python" -m voice_clone measure-speed --if-needed || speed_status=$?
if [ "$speed_status" -eq 130 ]; then
  exit 130
elif [ "$speed_status" -ne 0 ]; then
  echo "Speed test skipped, it will try again next time."
fi

if [ "$installed" -eq 1 ]; then
  if is_macos && ! was_reported blackhole && [ ! -d "$blackhole_driver" ]; then
    say_fail "BlackHole 2ch is not installed. Install it with: brew install --cask blackhole-2ch"
  fi
  if ! was_reported ffmpeg && ! command -v ffmpeg >/dev/null 2>&1; then
    say_fail "ffmpeg is not installed. You need it to train a voice. Install it with: brew install ffmpeg"
  fi
  if ! was_reported git && ! git_works; then
    say_fail "git is not installed. You need it to train a voice. Install it with: xcode-select --install"
  fi
fi

exec "$venv_python" -m voice_clone run
