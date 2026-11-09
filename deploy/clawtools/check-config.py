#!/usr/bin/env python3
"""Load a candidate with the installed Toolbox binary without changing the service."""
import json
import subprocess
import sys


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: check-config.py /absolute/path/to/candidate.yaml")
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-03-26", "capabilities": {},
            "clientInfo": {"name": "config-check", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    try:
        result = subprocess.run(
            ["/opt/mcp-toolbox/current", "--config", sys.argv[1], "--stdio",
             "--disable-reload", "--disable-version-check", "--log-level", "error"],
            input="".join(json.dumps(item) + "\n" for item in requests),
            text=True, capture_output=True, timeout=45, check=True,
        )
        responses = {item.get("id"): item for line in result.stdout.splitlines()
                     if (item := json.loads(line)).get("id") is not None}
        assert "serverInfo" in responses[1]["result"]
        listing = responses[2]["result"]
        assert not listing.get("nextCursor"), "Incomplete tool list"
        names = sorted(tool["name"] for tool in listing["tools"])
        assert len(names) == len(set(names)), "Duplicate tools"
    except (OSError, subprocess.SubprocessError, ValueError, KeyError,
            TypeError, AssertionError):
        # Native diagnostics may contain expanded credentials. Do not echo them.
        sys.exit("INVALID: candidate failed native loading/MCP check; do not apply. "
                 "Inspect native diagnostics only in a private server session.")
    print(json.dumps({"valid": True, "tools": names}, ensure_ascii=False))


if __name__ == "__main__":
    main()
