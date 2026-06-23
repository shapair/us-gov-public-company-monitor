#!/usr/bin/env python3
"""Minimal asyncio HTTP CONNECT proxy for development use.

Some Docker Desktop / macOS setups cannot complete TLS handshakes from inside
containers to certain public APIs (api.usaspending.gov, raw.githubusercontent.com,
etc.). Running this proxy on the host lets containers route outbound HTTPS
through the host's working network stack.

Usage:
    python scripts/host_connect_proxy.py

Then set in your container environment:
    HTTPS_PROXY=http://host.docker.internal:8788
    NO_PROXY=db,localhost,127.0.0.1

The proxy only handles CONNECT tunnels; it does not decrypt traffic.
"""
from __future__ import annotations

import asyncio
import os
import signal
import sys

# Avoid forwarding the host's own proxy settings to upstream connections,
# which could create a loop.
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8788
CHUNK_SIZE = 65_536


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            data = await reader.read(CHUNK_SIZE)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionResetError, BrokenPipeError, OSError):
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def _handle_client(
    client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter
) -> None:
    addr = client_writer.get_extra_info("peername")
    try:
        request_line = await client_reader.readline()
        if not request_line.startswith(b"CONNECT "):
            client_writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            await client_writer.drain()
            return

        target = request_line.split()[1].decode("ascii", errors="replace")
        host, port = target.rsplit(":", 1)
        port = int(port)

        # Drain remaining request headers.
        while True:
            line = await client_reader.readline()
            if line in (b"\r\n", b"\n", b""):
                break

        try:
            remote_reader, remote_writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=30
            )
        except Exception as exc:
            client_writer.write(
                f"HTTP/1.1 502 Bad Gateway: {exc}\r\n\r\n".encode()
            )
            await client_writer.drain()
            return

        client_writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
        await client_writer.drain()

        await asyncio.gather(
            _pipe(client_reader, remote_writer),
            _pipe(remote_reader, client_writer),
        )
    except Exception:
        pass
    finally:
        try:
            client_writer.close()
            await client_writer.wait_closed()
        except Exception:
            pass


async def _heartbeat(stop_event: asyncio.Event) -> None:
    """Emit periodic output so long-running background task runners see activity."""
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=60.0)
        except asyncio.TimeoutError:
            print("[host_connect_proxy] heartbeat", flush=True)


async def run(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    server = await asyncio.start_server(_handle_client, host, port)
    print(f"[host_connect_proxy] Listening on {host}:{port}", flush=True)
    print(
        f"[host_connect_proxy] Containers can use HTTPS_PROXY=http://host.docker.internal:{port}",
        flush=True,
    )

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler(signum, frame):  # noqa: ARG001
        print("\n[host_connect_proxy] Shutting down...", flush=True)
        stop_event.set()

    loop.add_signal_handler(signal.SIGINT, _signal_handler, None, None)
    loop.add_signal_handler(signal.SIGTERM, _signal_handler, None, None)

    async with server:
        tasks = [
            asyncio.create_task(stop_event.wait()),
            asyncio.create_task(server.serve_forever()),
            asyncio.create_task(_heartbeat(stop_event)),
        ]
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        # Cancel remaining tasks gracefully.
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    server.close()
    await server.wait_closed()
    print("[host_connect_proxy] Stopped", flush=True)


def main(argv: list[str]) -> int:
    host = os.environ.get("HOST_CONNECT_PROXY_HOST", DEFAULT_HOST)
    port = int(os.environ.get("HOST_CONNECT_PROXY_PORT", DEFAULT_PORT))
    if argv[1:]:
        port = int(argv[1])
    asyncio.run(run(host, port))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
