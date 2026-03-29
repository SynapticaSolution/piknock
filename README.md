# PiKnock

> *Knock knock... wake up!* A Wake-on-LAN controller with web UI, designed for Raspberry Pi.

**[English](README.md)** | **[Italiano](README.it.md)**

Turn on your PCs remotely from a browser — works over your LAN or via a direct Ethernet cable between the Pi and your machine.

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.7+-green)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)

## Features

- **Web-based device management** — add, edit, remove target PCs from the browser
- **Multi-method WOL** — sends magic packets via multiple broadcast addresses for reliability
- **Direct Ethernet support** — wake a PC connected directly to the Pi with no router needed
- **Zero Python dependencies** — uses only the standard library
- **Single file server** — one Python file, easy to deploy and maintain
- **REST API** — automate with `curl` or scripts
- **Responsive UI** — works on desktop and mobile

## How It Works

PiKnock runs a lightweight HTTP server on your Raspberry Pi. When you click "Wake" in the web UI, it sends [Wake-on-LAN magic packets](https://en.wikipedia.org/wiki/Wake-on-LAN) to the target PC's network card, which powers on the machine.

**Two network scenarios are supported:**

```
Scenario 1: LAN (via router)                Scenario 2: Direct Ethernet
┌──────────┐    ┌────────┐    ┌────┐        ┌──────────┐  ethernet  ┌────────┐
│ Browser  │───→│ Router │───→│ Pi │        │    Pi    │═══════════│   PC   │
└──────────┘    └────────┘    └────┘        │ 10.0.0.1 │           │10.0.0.2│
                                 │           └──────────┘           └────────┘
                            magic packet
                                 ↓
                              ┌────┐
                              │ PC │
                              └────┘
```

## Requirements

- Raspberry Pi (any model) with Python 3.7+
- `wakeonlan` package: `sudo apt install wakeonlan`
- Target PC with WOL enabled in BIOS

## Quick Install

```bash
git clone https://github.com/SynapticaSolution/piknock.git
cd piknock
sudo ./install.sh
```

The installer will:
1. Install `wakeonlan`
2. Deploy PiKnock to `/opt/piknock`
3. Set up a systemd service (auto-start on boot)
4. Optionally configure a direct Ethernet connection

## Manual Install

```bash
# Install dependency
sudo apt install wakeonlan

# Copy files
sudo mkdir -p /opt/piknock
sudo cp piknock.py /opt/piknock/
sudo cp config.example.json /opt/piknock/config.json

# Run
python3 /opt/piknock/piknock.py
```

## Update

```bash
cd piknock
git pull
sudo cp piknock.py /opt/piknock/
sudo systemctl restart piknock
```

## Development

```bash
cp config.example.json config.json
python3 piknock.py
# Open http://localhost:8080
```

## Configuration

Devices are stored in `config.json`:

```json
{
  "devices": [
    {
      "id": "abc123",
      "name": "My Desktop",
      "mac": "AA:BB:CC:DD:EE:FF",
      "broadcast": "192.168.1.255",
      "description": "Main PC on LAN"
    }
  ],
  "server": {
    "port": 8080,
    "host": "0.0.0.0"
  }
}
```

You can edit this file directly or use the web UI.

## Direct Ethernet Setup

To wake a PC connected directly to the Pi (no router):

**On the Raspberry Pi** (handled by `install.sh`):
- Set `eth0` to static IP `10.0.0.1/24`

**On the target PC**:
- Set the Ethernet interface to static IP `10.0.0.2`, subnet `255.255.255.0`, no gateway

Then add the device in PiKnock with broadcast address `10.0.0.255`.

## BIOS Setup for WOL

Enable these in your target PC's BIOS:
- **Wake on LAN**: Enabled
- **Wake on PCIe/PCI**: Enabled
- **ERP Support**: Disabled
- **Deep Sleep**: Disabled

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/devices` | List all devices |
| `POST` | `/api/devices` | Add a device |
| `PUT` | `/api/devices/{id}` | Update a device |
| `DELETE` | `/api/devices/{id}` | Remove a device |
| `POST` | `/api/wake/{id}` | Send WOL to device |
| `GET` | `/api/status` | Server info |

**Example:**
```bash
# Wake a device
curl -X POST http://raspberrypi:8080/api/wake/abc123

# Add a device
curl -X POST http://raspberrypi:8080/api/devices \
  -H "Content-Type: application/json" \
  -d '{"name":"Server","mac":"AA:BB:CC:DD:EE:FF","broadcast":"192.168.1.255"}'
```

## License

MIT - See [LICENSE](LICENSE)

---

Made by [Synaptica](https://www.synaptica-solution.com)
