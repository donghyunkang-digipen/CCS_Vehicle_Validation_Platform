# Connected Vehicle Validation Platform

A personal portfolio project for a fully synthetic, production-inspired connected-vehicle validation environment. All vehicle behavior, CAN identifiers, payloads, and tests in this repository are fictional and do not represent any OEM or supplier system.

## Implemented milestone: v0.2.0 DBC-Based CAN Modeling

```text
Engine ECU state -> cantools + synthetic_vehicle.dbc -> SocketCAN vcan0
SocketCAN vcan0 -> cantools + synthetic_vehicle.dbc -> CCU display
```

The DBC is the single source of truth for the two fictional standard (11-bit) CAN frames. The engine ECU encodes signals from it every 500 ms by default, and the CCU decodes received payloads through the same model:

| CAN ID | DBC message | DBC signals | Payload |
| --- | --- | --- | --- |
| `0x180` | `EngineStatus` | `IgnitionOn`, `EngineRunning` | 1 byte; one-bit unsigned signals |
| `0x181` | `VehicleSpeed` | `VehicleSpeedKph` | 2-byte big-endian unsigned signal; 0.1 km/h scale; 0.0-6553.5 km/h |

All names, identifiers, signals, values, and payloads are invented for this portfolio project. MQTT, HTTP, databases, Docker, frontends, and fault injection remain outside this milestone.

## Windows 11 and WSL2 workflow

Windows is the host/editor environment only. Run Python, tests, `ip`, and all SocketCAN tools inside Ubuntu under WSL2.

```text
Windows: C:\CCS_Vehicle_Validation_Platform
WSL2:    /mnt/c/CCS_Vehicle_Validation_Platform
```

From a fresh Ubuntu terminal:

```bash
cd /mnt/c/CCS_Vehicle_Validation_Platform
pwd
```

The expected output is `/mnt/c/CCS_Vehicle_Validation_Platform`. Linux filesystem operations under `/mnt/c` can be slower than under the native WSL filesystem, but that does not prevent v0.2.0 from running.

## Install Ubuntu packages and project dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip iproute2 kmod can-utils

cd /mnt/c/CCS_Vehicle_Validation_Platform
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

`requirements.txt` and `requirements-dev.txt` are also provided for requirements-file workflows.

## Check WSL2 kernel support for `vcan`

Confirm the environment and inspect its kernel:

```bash
uname -a
grep -i microsoft /proc/version
```

Attempt to load and inspect `vcan`:

```bash
sudo modprobe vcan
lsmod | grep '^vcan' || true
modinfo vcan 2>/dev/null | head || true
```

No `lsmod` result is not conclusive by itself: `vcan` can be built into the kernel rather than loaded as a module. The decisive functional check is whether the interface can be created. The project setup script performs that check while configuring it:

```bash
cd /mnt/c/CCS_Vehicle_Validation_Platform
sudo bash scripts/setup_vcan.sh
```

Invoking the script through `bash` avoids relying on Linux executable permission bits on the Windows-mounted filesystem. The script loads `vcan`, creates `vcan0` only if absent, brings it up, and displays its details. It is safe to rerun.

If `modprobe` reports `Module vcan not found`, try the functional check directly because support could be built in:

```bash
sudo ip link add dev vcan0 type vcan
sudo ip link set vcan0 up
ip -details link show vcan0
```

If `vcan0` already exists, `ip link add` reports `File exists`; continue with the remaining commands. If the add command instead reports `Operation not supported` or `Unknown device type`, the running WSL2 kernel lacks usable `vcan` support.

Where the kernel exposes its build configuration, inspect it with:

```bash
uname -r
test -r /proc/config.gz && zgrep 'CONFIG_CAN\|CONFIG_CAN_VCAN' /proc/config.gz
test -r "/boot/config-$(uname -r)" && grep 'CONFIG_CAN\|CONFIG_CAN_VCAN' "/boot/config-$(uname -r)"
```

`CONFIG_CAN=y` or `m` and `CONFIG_CAN_VCAN=y` or `m` indicate support. A missing option or `CONFIG_CAN_VCAN is not set` means the kernel was built without it. Not every WSL kernel exposes a config file, so the functional `ip link add` result remains the key test.

If support is absent, update WSL from an elevated Windows PowerShell:

```powershell
wsl --update
wsl --shutdown
```

Open a new Ubuntu terminal and retry. If the updated kernel still lacks the option, WSL2 must be configured with a custom kernel built with CAN and VCAN support.

The `vcan0` setup is not persistent after WSL shuts down or its virtual machine restarts. Rerun the setup script in a new WSL session.

## Verify `vcan0` with can-utils

```bash
ip -details link show vcan0
candump -L vcan0
```

`candump` waits silently until traffic arrives. Leave it running and start the ECU in another Ubuntu terminal. Stop it with `Ctrl+C`.

## Run the simulation

Open three Ubuntu/WSL2 terminals. The Python programs do not require `sudo`.

Terminal 1 - CCU receiver:

```bash
cd /mnt/c/CCS_Vehicle_Validation_Platform
source .venv/bin/activate
ccu-receiver
```

Terminal 2 - raw CAN observation:

```bash
cd /mnt/c/CCS_Vehicle_Validation_Platform
candump -L vcan0
```

Terminal 3 - Engine ECU simulator:

```bash
cd /mnt/c/CCS_Vehicle_Validation_Platform
source .venv/bin/activate
engine-ecu
```

The receiver displays raw identifiers and bytes plus decoded synthetic values. Stop each process with `Ctrl+C`.

Optional simulator arguments:

```bash
engine-ecu --speed 65.2 --period 1.0
engine-ecu --ignition-off --engine-off --speed 0
```

Equivalent module commands are `python -m connected_vehicle_validation.can.ccu_receiver` and `python -m connected_vehicle_validation.can.engine_ecu`.

## Run tests

Tests cover DBC loading, message and signal metadata, encoding, decoding, scaling, boundaries, malformed inputs, CLI parsing, and in-memory CAN behavior. They do not require root privileges or `vcan0`:

```bash
cd /mnt/c/CCS_Vehicle_Validation_Platform
source .venv/bin/activate
python -m pytest
```

### Pytest cache permissions under `/mnt/c`

If pytest reports `PytestCacheWarning: could not create cache path`, inspect the
Windows-backed directory from WSL:

```bash
ls -ld .pytest_cache .pytest_cache/v .pytest_cache/v/cache 2>/dev/null
```

This can happen when `.pytest_cache` was created by a different Windows or sandbox
account whose Windows ACL is not writable through WSL. It is generated, ignored
test data, so after confirming that exact path, remove it and let pytest recreate
it from WSL:

```bash
rm -rf -- /mnt/c/CCS_Vehicle_Validation_Platform/.pytest_cache
python -m pytest
```

Do not disable pytest's cache provider merely to conceal this warning. Keeping the
repository under `/mnt/c` is supported for v0.2.0, but a repository stored under the
native WSL filesystem (for example `~/projects/`) provides faster Linux file I/O
and avoids Windows/WSL permission translation issues. Moving it is recommended for
long-term Linux-first development, not required for this milestone.

## Repository structure

```text
scripts/setup_vcan.sh                         Linux vcan0 setup
src/connected_vehicle_validation/can/
  synthetic_vehicle.dbc                      Fictional CAN message and signal model
  protocol.py                                 DBC loader and encoding/decoding API
  engine_ecu.py                               Periodic CAN transmitter
  ccu_receiver.py                             CAN receiver and display
tests/test_dbc.py                              Direct DBC and signal tests
tests/                                         Protocol, ECU, and receiver tests
```

The DBC is included as Python package data, so editable and wheel installations load the same model through `importlib.resources`. Python does not duplicate bit positions, byte order, scaling, lengths, or CAN identifiers; `cantools` reads those properties from the packaged DBC.

## Manual acceptance checklist

- [ ] All runtime commands are executed in Ubuntu/WSL2, not Windows PowerShell.
- [ ] `sudo bash scripts/setup_vcan.sh` shows `vcan0` in the `UP` state.
- [ ] `ip -details link show vcan0` identifies a `vcan` interface.
- [ ] `ccu-receiver` reports that it is listening on `vcan0`.
- [ ] Starting `engine-ecu` produces repeating `0x180` and `0x181` frames.
- [ ] `candump -L vcan0` displays the raw `180` and `181` frames.
- [ ] Receiver output shows ignition on, engine running, and speed `42.5` km/h.
- [ ] `python -m pytest` completes with all tests passing.
- [ ] The packaged DBC loads and defines messages `EngineStatus` (`0x180`) and `VehicleSpeed` (`0x181`).
- [ ] Default raw payloads remain `03` for both engine flags on and `01 A9` for 42.5 km/h.
- [ ] Boundary speeds 0.0 and 6553.5 km/h encode/decode successfully; out-of-range and malformed inputs are rejected.

## Known limitations

- SocketCAN runs inside Ubuntu/WSL2, not directly on Windows.
- Some WSL2 kernels may lack `CONFIG_CAN_VCAN`; use the checks above to detect this.
- The simulator broadcasts a fixed state until restarted with different options.
- The fictional DBC intentionally models only the two v0.1-compatible frames.
- There is no fault injection, persistence, remote transport, or dashboard.
- The setup script configures `vcan0` only for the current WSL virtual-machine session.
