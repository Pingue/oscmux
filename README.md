# oscmux mod

This program redirects Open Sound Control messages coming from an arbitrary number of local ports to an arbitrary number of
host ports with arbitrary delays and filtering according to path and format strings.

This version is modified to support a fixed path translate.

Example: only redirect messages matching path '/user/fader_1' from from local port 12345 to local port 9000 but renamed as /myinputvalue
	
	oscmux  -p /user/fader_1 -r /myinputvalue -i osc.udp://localhost:12345 -o osc.udp://localhost:9000
	

Note: Original without modifications at [https://github.com/OpenMusicKontrollers/oscmux](https://github.com/OpenMusicKontrollers/oscmux)

## command line usage

redirect messages from local port 3333 to local ports 4444 and 5555

	oscmux -i osc://localhost:3333 -o osc://localhost:4444 -o osc://localhost:5555

multiplex messages from local ports 1111 and 2222 and send them to port 4444 on 10.0.0.1 with a delay of 0.5 seconds
	
	oscmux -i osc://localhost:1111 -i osc://localhost:2222 -d 0.5 -o osc://10.0.0.1:4444

redirect messages from local port 2222 to local port 3333 with a delay of 1.1 seconds and to port 4444 on 10.0.0.2 with a delay of 4.3 seconds

	oscmux -i osc://localhost:2222 -d 1.1 -o osc://localhost:3333 -d 4.3 -o osc://10.0.0.2:4444

multiplex messages from local ports 1111 (via udp), 2222 (via udp) and 3333 (via tcp) and send them to local ports 4444 (udp), 5555 (udp) and 6666 (tcp)

	oscmux -i osc://localhost:1111 -i osc.udp://localhost:2222 -i osc.tcp://localhost:3333 -o osc://localhost:4444 -o osc.udp://localhost:5555 -o osc.tcp://localhost:6666

only redirect messages matching path '/hello' from local port 1313 to port 6666 on 10.0.0.10 with a delay of 3.1415926 seconds

	oscmux -p /hello -i osc://localhost:1313 -d 3.1415926 -o osc://10.0.0.10:6666

only redirect messages with a single integer argument followed by a boolean true from local port 1313 (via tcp) to local port 1414 (tcp) with no delay

	oscmux -f iT -i osc.tcp://localhost:1313 -o osc.tcp://localhost:1414

redirect messages matching path '/one' from local port 1212 to local port 1313 and redirect messages matching path '/two' from local port 1212 to local port 1414

	oscmux -p /one -i osc://localhost:1212 -o osc://localhost:1313 -p /two -i osc://localhost:1212 -o osc://localhost:1414

redirect messages from local port 1212 to local port 1313 enabling queueing messages when told so by a offset timestamp

	oscmux -Q -i osc://localhost:1212 -o osc://localhost:1313

redirect messages from local port 1212 to local port 1313 disabling queueing (which is the default) messages when told so by a offset timestamp

	oscmux -q -i osc://localhost:1212 -o osc://localhost:1313

# Docker

Images are published to `ghcr.io/pingue/oscmux` (tagged `X.Y.Z`, `X.Y` and `latest`).
Arguments are passed straight to `oscmux`:

	docker run --rm -p 9000:9000/udp ghcr.io/pingue/oscmux \
	  -i osc.udp://localhost:9000 -o osc.udp://192.168.1.50:9001

Notes:

- Only the port of an `-i` URL matters (it listens on all interfaces), and it must be published with `-p PORT:PORT/udp`.
- Inside the container `localhost` is the container itself, so give outputs a real host address, or use `--network host` on Linux.

# Development

Build (see INSTALL.md for dependencies) and run the tests:

	cmake -S . -B build
	cmake --build build
	pip install -r requirements-dev.txt
	pytest

The tests start the real binary, send OSC over UDP and inspect what it forwards. Set `OSCMUX_BIN` to test a different binary,
for example one built with `-fsanitize=address,undefined` (CI does this).

# Releases

Commits to `master` use [Conventional Commits](https://www.conventionalcommits.org/). After the tests pass, the release
workflow computes the next [semver](https://semver.org/) version: `feat` bumps minor, `fix`/`perf` bump patch, and `!` or a
`BREAKING CHANGE:` footer bumps major. Other types (`docs`, `ci`, `chore`, `test`, ...) don't release. When there is
something to release it publishes the Docker image, tags the commit `vX.Y.Z` and creates a GitHub release with notes grouped
by commit type.
