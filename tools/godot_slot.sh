#!/bin/bash
# Source this file, then call godot_slot_take <lane> before any Godot start.
# It caps the number of Godot processes that all agents on one machine run at the same time.
# Measure your own machine: a headless game used 1 to 1.5 GB and a windowed game 2.2 to 3.5 GB
# on a 32 GB Mac, so 6 was the cap there. Set GODOT_SLOT_MAX to change it.
# A slot is a dir ${SLOT_PREFIX}1 to ${SLOT_PREFIX}N (mkdir is atomic, so 2 agents never get the same slot).
# It also writes a row in work/manager/godot-slots.tsv, which the game-manager skill reads.
# godot_slot_free runs from the EXIT trap, so the slot goes when the script ends.
# Agents start a windowed game only through "$GODOT_BG" (tools/godot_bg.sh): it never takes focus.
#
# Example:
#   source tools/godot_slot.sh
#   godot_slot_take my-lane
#   godot --headless --path . -- --port 9300 &
#   GAME=$!          # godot_slot_free kills $GAME on exit
#
# Bash only. Under zsh BASH_SOURCE is empty, so set GODOT_SLOT_REPO.
if [ -n "${BASH_SOURCE[0]}" ]; then
	SLOT_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
else
	SLOT_REPO="${GODOT_SLOT_REPO:-$PWD}"
fi
SLOT_TSV="$SLOT_REPO/work/manager/godot-slots.tsv"
GODOT_BG="$SLOT_REPO/tools/godot_bg.sh"
GODOT_SLOT=""
SLOT_MAX="${GODOT_SLOT_MAX:-6}"
SLOT_PREFIX="${SLOT_PREFIX:-/tmp/godot-slot-}"
SLOT_HOLD_FILE="${SLOT_HOLD_FILE:-/tmp/godot-slot-hold}"

godot_record_hold_wait() {
	# A screen recording can set $SLOT_HOLD_FILE (content: expiry epoch seconds) so no other run takes the GPU.
	# Start no Godot run while it exists and has not expired; a stale file past its expiry is ignored.
	while [ -f "$SLOT_HOLD_FILE" ]; do
		local exp; exp=$(cat "$SLOT_HOLD_FILE" 2>/dev/null | tr -dc '0-9')
		[ -n "$exp" ] && [ "$(date +%s)" -ge "$exp" ] && break
		echo "godot slot: recording hold, waiting 5 s" >&2
		sleep 5
	done
}

# Optional: a remote Linux box runs heavy headless jobs. If GODOT points at your remote wrapper
# (set GODOT_REMOTE_PATTERN to a glob that matches it) and GODOT_LOCAL is not 1, the run takes no
# local slot: the remote box queues its own runs.
godot_on_remote() {
	[ -n "${GODOT_REMOTE_PATTERN:-}" ] || return 1
	[ "${GODOT_LOCAL:-0}" = 1 ] && return 1
	case "${GODOT:-$(command -v godot 2>/dev/null)}" in $GODOT_REMOTE_PATTERN) return 0 ;; esac
	return 1
}

godot_slot_take() {
	local lane="${1:-agent}"
	godot_on_remote && { trap godot_slot_free EXIT; return 0; }
	godot_record_hold_wait
	while true; do
		for n in $(seq 1 "$SLOT_MAX"); do
			if mkdir "${SLOT_PREFIX}$n" 2>/dev/null; then
				GODOT_SLOT="${SLOT_PREFIX}$n"
				echo "$lane $$" > "$GODOT_SLOT/owner"
				mkdir -p "$(dirname "$SLOT_TSV")"
				[ -f "$SLOT_TSV" ] || printf 'lane\tpid\tstarted\n' > "$SLOT_TSV"
				printf '%s\t%s\t%s\n' "$lane" "$$" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$SLOT_TSV"
				trap godot_slot_free EXIT
				return 0
			fi
		done
		echo "godot slot: all $SLOT_MAX taken, waiting 5 s" >&2
		sleep 5
	done
}

godot_slot_free() {
	[ -n "${GAME:-}" ] && kill "$GAME" 2>/dev/null
	[ -n "$GODOT_SLOT" ] || return 0
	rm -rf "$GODOT_SLOT"
	if [ -f "$SLOT_TSV" ]; then
		awk -F'\t' -v pid="$$" 'NR == 1 || $2 != pid' "$SLOT_TSV" > "$SLOT_TSV.tmp" && mv "$SLOT_TSV.tmp" "$SLOT_TSV"
	fi
	GODOT_SLOT=""
}
