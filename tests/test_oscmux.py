import subprocess
import time

import pytest
from pythonosc.osc_packet import OscPacket

from conftest import free_udp_port, url


# --- basic relaying ---------------------------------------------------------

def test_relays_a_message_unchanged(start, sink):
    out, port = sink(), free_udp_port()
    relay = start("-i", url(port), "-o", out.url)
    relay.send(port, "/hello", 1, 2.5, "text", True)
    assert out.messages(1) == [("/hello", [1, 2.5, "text", True])]


def test_distinct_addresses_are_preserved(start, sink):
    # Regression: the output path used to be cached from liblo's receive buffer,
    # so later messages came out with garbage addresses.
    out, port = sink(), free_udp_port()
    relay = start("-i", url(port), "-o", out.url)
    sent = [f"/p{i}/x{i * 7}" for i in range(12)]
    for address in sent:
        relay.send(port, address, 1)
    assert [a for a, _ in out.messages(12)] == sent


def test_fan_out_to_several_outputs(start, sink):
    a, b, port = sink(), sink(), free_udp_port()
    relay = start("-i", url(port), "-o", a.url, "-o", b.url)
    relay.send(port, "/fan", 7)
    assert a.messages(1) == [("/fan", [7])]
    assert b.messages(1) == [("/fan", [7])]


def test_multiplexes_several_inputs(start, sink):
    out, p1, p2 = sink(), free_udp_port(), free_udp_port()
    relay = start("-i", url(p1), "-i", url(p2), "-o", out.url)
    relay.send(p1, "/one", 1)
    relay.send(p2, "/two", 2)
    assert sorted(out.messages(2)) == [("/one", [1]), ("/two", [2])]


# --- filtering and routing --------------------------------------------------

def test_path_filter_drops_other_paths(start, sink):
    out, port = sink(), free_udp_port()
    relay = start("-p", "/only", "-i", url(port), "-o", out.url)
    relay.send(port, "/other", 1)
    relay.send(port, "/only", 2)
    relay.send(port, "/other/deeper", 3)
    assert out.messages() == [("/only", [2])]


def test_one_local_port_routes_to_many_outputs_by_path(start, sink):
    # The README's "one local port, different destinations per path" example.
    one, two, port = sink(), sink(), free_udp_port()
    relay = start("-p", "/one", "-i", url(port), "-o", one.url,
                  "-p", "/two", "-i", url(port), "-o", two.url)
    for address, value in [("/one", 1), ("/two", 2), ("/one", 3), ("/two", 4), ("/other", 5)]:
        relay.send(port, address, value)
    assert one.messages() == [("/one", [1]), ("/one", [3])]
    assert two.messages() == [("/two", [2]), ("/two", [4])]


def test_format_filter(start, sink):
    out, port = sink(), free_udp_port()
    relay = start("-f", "iT", "-i", url(port), "-o", out.url)
    relay.send(port, "/match", 5, True)
    relay.send(port, "/nomatch", 5, False)   # types "iF"
    relay.send(port, "/nomatch2", "text")    # types "s"
    assert out.messages() == [("/match", [5, True])]


# --- rewriting --------------------------------------------------------------

def test_rename_rewrites_the_path_and_keeps_arguments(start, sink):
    out, port = sink(), free_udp_port()
    relay = start("-p", "/user/fader_1", "-r", "/myinputvalue", "-i", url(port), "-o", out.url)
    relay.send(port, "/user/fader_1", 0.5)
    assert out.messages(1) == [("/myinputvalue", [0.5])]


def test_rename_applies_only_to_the_next_output(start, sink):
    renamed, plain, port = sink(), sink(), free_udp_port()
    relay = start("-i", url(port), "-r", "/renamed", "-o", renamed.url, "-o", plain.url)
    relay.send(port, "/orig", 1)
    assert renamed.messages(1) == [("/renamed", [1])]
    assert plain.messages(1) == [("/orig", [1])]


# --- bundles and delay ------------------------------------------------------

def test_bundles_stay_bundles(start, sink):
    out, port = sink(), free_udp_port()
    relay = start("-i", url(port), "-o", out.url)
    relay.send_bundle(port, [("/a", 1), ("/b", 2)])
    datagrams = out.datagrams(1)
    assert len(datagrams) == 1 and datagrams[0].startswith(b"#bundle")
    got = [(tm.message.address, list(tm.message.params)) for tm in OscPacket(datagrams[0]).messages]
    assert got == [("/a", [1]), ("/b", [2])]


def test_delay_sets_a_future_timetag(start, sink):
    out, port = sink(), free_udp_port()
    relay = start("-i", url(port), "-d", "2.0", "-o", out.url)
    sent_at = time.time()
    relay.send(port, "/later", 1)
    (datagram,) = out.datagrams(1)
    assert datagram.startswith(b"#bundle")
    (timed,) = OscPacket(datagram).messages
    assert timed.message.address == "/later"
    assert 1.5 < timed.time - sent_at < 2.5


# --- command line -----------------------------------------------------------

def run(binary, *args):
    return subprocess.run([str(binary), *args], capture_output=True, text=True, timeout=10)


@pytest.mark.parametrize("args", [
    [],
    ["-i", "osc.udp://localhost:%d"],            # input but no output
    ["-o", "osc.udp://127.0.0.1:9"],             # output but no input
    ["-x"],                                      # unknown option
    ["-p"],                                      # option missing its argument
])
def test_bad_command_lines_exit_nonzero(binary, args):
    args = [a % free_udp_port() if "%d" in a else a for a in args]
    result = run(binary, *args)
    assert result.returncode == 1
    assert result.stderr.strip()


def test_output_before_input_is_an_error_not_a_crash(binary):
    # Regression: this used to segfault (uninitialised group pointer).
    result = run(binary, "-o", "osc.udp://127.0.0.1:9", "-i", url(free_udp_port()))
    assert result.returncode == 1
    assert "before any input" in result.stderr
