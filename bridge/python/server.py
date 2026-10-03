"""MCP server that wraps a running game's JSON bridge (127.0.0.1, newline-delimited JSON).

A Claude Code session can then read the game state, send real input and take player-camera
screenshots through MCP tools. The same server works for the Godot and the Unity bridge,
because both speak the same protocol. Start the game first. Transport: stdio.

Env:
  BRIDGE_PORT         the game's bridge port (default 9177)
  GAME_NAME           the name in the server instructions (default "the game")
  GAME_WORLD_RULES    a few lines on units, axes and cameras; agents read them before they move things

The tools below are the engine-agnostic set. Your game must answer these commands
(return {"error": "..."} for one it does not have). Add game tools at the bottom, as the example shows.
"""
import json
import os
import sys
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bridge_client import Bridge, BridgeError  # noqa: E402

from mcp.server.mcpserver import MCPServer  # noqa: E402

GAME_NAME = os.environ.get("GAME_NAME", "the game")
WORLD_RULES = os.environ.get("GAME_WORLD_RULES", (
    "World rules:\n"
    "- Units are metres. Y is up.\n"
    "- Screenshots come from the viewport of the player camera; they need a windowed game, never window focus.\n"
))

mcp = MCPServer(name="game", instructions=f"Tools to see and drive {GAME_NAME} while it runs. " + WORLD_RULES)
_bridge = Bridge(port=int(os.environ.get("BRIDGE_PORT", "9177")))


def _call(cmd: str, **args: Any) -> str:
    try:
        return json.dumps(_bridge.call(cmd, **args))
    except BridgeError as e:
        return json.dumps({"error": str(e)})


def _args(**kw: Any) -> dict:
    """Drop the args the caller left out, so the game uses its defaults."""
    return {k: v for k, v in kw.items() if v is not None}


@mcp.tool(description="Check that the game answers on the bridge.")
def ping() -> str:
    return _call("ping")


@mcp.tool(description="Get the live game state as JSON (seed, game time, scene, camera, player, HUD, controls). "
        "Call this first. " + WORLD_RULES)
def get_state() -> str:
    return _call("get_state")


@mcp.tool(description="Read one game value by key. The game lists its keys in get_state.")
def get_value(key: str) -> str:
    return _call("get_value", key=key)


@mcp.tool(description="Set one game value by key. The game allows only a fixed list of keys; an unknown key returns an error.")
def set_value(key: str, value: Any) -> str:
    return _call("set_value", key=key, value=value)


@mcp.tool(description="Simulate player input: hold one input action for `seconds` of game time (0 = one tap). "
        "The action names are in get_state (controls).")
def sim_input(action: str, seconds: float = 0.0) -> str:
    return _call("sim_input", action=action, seconds=seconds)


@mcp.tool(description="Return n values from the game's seeded RNG. reseed: reset it to the --seed value first. "
        "Use it to check that a run is deterministic.")
def rng_sample(n: int = 4, reseed: bool = False) -> str:
    return _call("rng_sample", n=n, reseed=reseed)


@mcp.tool(description="Save a PNG from the player camera viewport. path is relative to the game repo (e.g. "
        "shots/test.png) or absolute. Returns the path and size; open the file with Read.")
def screenshot(path: str = "shots/screenshot.png") -> str:
    return _call("screenshot", path=path)


@mcp.tool(description="Set the game window size for a capture, size [w, h] in pixels. Omit size to read it.")
def window_size(size: Optional[list[int]] = None) -> str:
    return _call("window_size", **_args(size=size))


@mcp.tool(description="Send any bridge command with a JSON object of args. Use it for game commands that have no "
        "tool of their own.")
def bridge(cmd: str, args: Optional[dict[str, Any]] = None) -> str:
    return _call(cmd, **(args or {}))


@mcp.tool(description="Quit the running game.")
def quit() -> str:
    return _call("quit")


# Example of a game tool (from a submarine game). Write a full description: the agent reads only this.
#
# @mcp.tool(description="Fire one torpedo along the view direction. kind: standard or heavy. Returns ok, id and "
#       "reload_s, or ok false while it reloads or when the rack is empty. Read the flight with get_state.")
# def fire_torpedo(kind: str = "standard") -> str:
#   return _call("fire_torpedo", kind=kind)


if __name__ == "__main__":
    mcp.run()
