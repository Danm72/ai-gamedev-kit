#!/bin/bash
# Start a windowed Godot that never takes keyboard focus. Same args as `godot`.
# Example: tools/godot_bg.sh --path . -- --port 9288 &
# Use it when agents run windowed games (for screenshots) on the machine you work on.
#
# macOS: Godot 4.7 activates itself on start (show_window -> activateApplication, plus the
# "unbundled window activation hack"). No project setting, LSUIElement copy or `open -g` stops that.
# So this script loads tools/godot_bg/nofocus.dylib into the stock Godot.app binary.
# The dylib makes the activation calls no-ops and puts the window at the back of the window list.
# The window stays on screen, so frames render and a bridge `screenshot` works.
# Godot.app ships with allow-dyld-environment-variables + disable-library-validation, so no re-signing.
# The dylib is built from nofocus.m on first use (needs the Xcode command line tools).
#
# Linux: the stock godot on a virtual X screen (xvfb-run). No focus is at stake there.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "$(uname)" != "Darwin" ]; then
	GODOT_BIN="${GODOT:-$(command -v godot)}"
	for a in "$@"; do
		case "$a" in
			--headless|--import) exec "$GODOT_BIN" "$@" ;;
			--) break ;;
		esac
	done
	xvfb-run -a -s "-screen 0 1920x1080x24" "$GODOT_BIN" "$@" < /dev/null &
	XVFB_PID=$!
	trap 'pkill -TERM -P "$XVFB_PID" 2>/dev/null; kill -TERM "$XVFB_PID" 2>/dev/null' TERM INT HUP
	set +e
	wait "$XVFB_PID"
	rc=$?
	# A trapped signal ends the first wait early: wait again for xvfb-run to stop its X server.
	kill -0 "$XVFB_PID" 2>/dev/null && wait "$XVFB_PID" && rc=$?
	exit $rc
fi

GODOT_BIN="${GODOT_APP_BIN:-/Applications/Godot.app/Contents/MacOS/Godot}"
SRC="$DIR/godot_bg/nofocus.m"
LIB="$DIR/godot_bg/nofocus.dylib"

# A headless or import run has no window: start plain Godot, without the dylib.
for a in "$@"; do
	case "$a" in
		--headless|--import) exec "$GODOT_BIN" "$@" ;;
		--) break ;;
	esac
done

if [ ! -f "$LIB" ] || [ "$SRC" -nt "$LIB" ]; then
	clang -dynamiclib -arch "$(uname -m)" -framework AppKit -o "$LIB.tmp.$$" "$SRC"
	mv -f "$LIB.tmp.$$" "$LIB"
fi

# The bundle id env and a non-tty stdin also skip Godot's activation hack (a second guard).
export DYLD_INSERT_LIBRARIES="$LIB"
export __CFBundleIdentifier="org.godotengine.godot"
exec "$GODOT_BIN" "$@" < /dev/null
