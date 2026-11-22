"""Black-box tests: run the real oscmux binary, send OSC over UDP, and inspect
the datagrams it forwards."""

import os
import socket
import subprocess
import time
from pathlib import Path

import pytest
from pythonosc.osc_bundle_builder import IMMEDIATELY, OscBundleBuilder
from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.osc_packet import OscPacket

ROOT = Path(__file__).resolve().parent.parent


def _find_binary() -> Path:
    candidates = [os.environ.get("OSCMUX_BIN"), ROOT / "build" / "oscmux", ROOT / "oscmux"]
    for c in candidates:
        if c and Path(c).is_file():
            return Path(c)
    pytest.exit(
        "oscmux binary not found. Build it (cmake -B build && cmake --build build) "
        "or set OSCMUX_BIN.", returncode=2)


@pytest.fixture(scope="session")
def binary() -> Path:
    return _find_binary()


def free_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _bound_udp_ports() -> set:
    ports = set()
    for table in ("/proc/net/udp", "/proc/net/udp6"):
        try:
            with open(table) as f:
                next(f)
                for line in f:
                    ports.add(int(line.split()[1].split(":")[1], 16))
        except OSError:
            pass
    return ports


class Sink:
    """A UDP socket standing in for a downstream OSC receiver."""

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.url = f"osc.udp://127.0.0.1:{self.port}"

    def datagrams(self, count=None, timeout=3.0, idle=0.3) -> list:
        """Collect raw datagrams. With ``count``, stop as soon as that many have
        arrived (or after ``timeout``). Without it, stop after ``idle`` seconds
        of silence, which is how tests assert that nothing else was forwarded."""
        out = []
        deadline = time.monotonic() + timeout
        while count is None or len(out) < count:
            self.sock.settimeout(idle if count is None else max(0.0, deadline - time.monotonic()))
            try:
                out.append(self.sock.recvfrom(65535)[0])
            except (socket.timeout, BlockingIOError):
                break
        return out

    def messages(self, count=None, **kw) -> list:
        """Received messages as (address, params), flattening bundles."""
        msgs = []
        for d in self.datagrams(count, **kw):
            msgs.extend((tm.message.address, list(tm.message.params))
                        for tm in OscPacket(d).messages)
        return msgs

    def close(self):
        self.sock.close()


class Relay:
    """A running oscmux process plus helpers to talk to its input ports."""

    def __init__(self, binary, args):
        self.args = [str(a) for a in args]
        self.proc = subprocess.Popen([str(binary), *self.args],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        self._client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def wait_listening(self, *ports, timeout=5.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise AssertionError(f"oscmux exited early ({self.proc.returncode}): "
                                     f"{self.proc.stderr.read().decode()}")
            if not os.path.exists("/proc/net/udp"):  # non-Linux: fall back to a pause
                time.sleep(0.5)
                return
            if set(ports) <= _bound_udp_ports():
                return
            time.sleep(0.02)
        raise AssertionError(f"oscmux did not start listening on {ports}")

    def send(self, port, address, *args):
        b = OscMessageBuilder(address)
        for a in args:
            b.add_arg(a)
        self._client.sendto(b.build().dgram, ("127.0.0.1", port))

    def send_bundle(self, port, messages, timetag=IMMEDIATELY):
        bundle = OscBundleBuilder(timetag)
        for address, *args in messages:
            b = OscMessageBuilder(address)
            for a in args:
                b.add_arg(a)
            bundle.add_content(b.build())
        self._client.sendto(bundle.build().dgram, ("127.0.0.1", port))

    def stop(self):
        self.proc.kill()
        self.proc.wait()
        self.proc.stderr.close()
        self._client.close()


@pytest.fixture
def start(binary):
    """start("-i", "osc.udp://localhost:PORT", "-o", sink.url) -> Relay (waits
    until every -i port is listening)."""
    relays = []

    def _start(*args):
        relay = Relay(binary, args)
        relays.append(relay)
        in_ports = [int(args[i + 1].rsplit(":", 1)[1])
                    for i, a in enumerate(args) if a == "-i"]
        relay.wait_listening(*in_ports)
        return relay

    yield _start
    for r in relays:
        r.stop()


@pytest.fixture
def sink():
    sinks = []

    def _sink():
        s = Sink()
        sinks.append(s)
        return s

    yield _sink
    for s in sinks:
        s.close()


@pytest.fixture
def in_port():
    return free_udp_port


def url(port):
    return f"osc.udp://localhost:{port}"
