#!/usr/bin/env python3
"""
PiKnock - Raspberry Pi Wake-on-LAN Server
A lightweight WOL controller with web UI for Raspberry Pi.
https://github.com/SynapticaSolution/piknock
"""

import json
import re
import shutil
import subprocess
import threading
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"
CONFIG_LOCK = threading.Lock()
MAC_REGEX = re.compile(r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$")

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def load_config():
    with CONFIG_LOCK:
        if not CONFIG_FILE.exists():
            default = {"devices": [], "server": {"port": 8080, "host": "0.0.0.0"}}
            CONFIG_FILE.write_text(json.dumps(default, indent=2))
            return default
        return json.loads(CONFIG_FILE.read_text())


def save_config(config):
    with CONFIG_LOCK:
        CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n")


def normalize_mac(mac):
    """Normalize MAC to uppercase colon-separated format."""
    mac = mac.upper().replace("-", ":")
    if not MAC_REGEX.match(mac):
        return None
    return mac


# ---------------------------------------------------------------------------
# WOL logic
# ---------------------------------------------------------------------------


def send_wol(mac, broadcast):
    """Send WOL magic packet via multiple methods for reliability."""
    results = {"success": False, "methods": [], "errors": []}

    commands = [
        (["wakeonlan", mac], "wakeonlan (default broadcast)"),
        (["wakeonlan", "-i", broadcast, mac], f"wakeonlan -i {broadcast}"),
        (["wakeonlan", "-i", "255.255.255.255", mac], "wakeonlan (global broadcast)"),
    ]

    for cmd, label in commands:
        try:
            subprocess.run(cmd, capture_output=True, timeout=5, check=True)
            results["methods"].append(label)
            results["success"] = True
        except FileNotFoundError:
            results["errors"].append(f"{label}: wakeonlan not installed")
            break
        except subprocess.CalledProcessError as e:
            results["errors"].append(f"{label}: {e.stderr.decode().strip()}")
        except subprocess.TimeoutExpired:
            results["errors"].append(f"{label}: timeout")

    return results


def check_wakeonlan():
    """Check if wakeonlan is available."""
    return shutil.which("wakeonlan") is not None


# ---------------------------------------------------------------------------
# HTML UI
# ---------------------------------------------------------------------------

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PiKnock</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --primary:#007acc;--accent:#00d4ff;--bg:#0a0a0f;
  --glass-bg:rgba(255,255,255,0.05);--glass-border:rgba(0,212,255,0.15);
  --text:#e0e0e0;--text-dim:#888;--danger:#e74c3c;--success:#2ecc71;
}
body{
  background:var(--bg);
  background-image:radial-gradient(ellipse at top,rgba(0,122,204,0.15) 0%,transparent 60%);
  color:var(--text);font-family:'Segoe UI',system-ui,-apple-system,sans-serif;
  min-height:100vh;padding:20px;
}
.container{max-width:900px;margin:0 auto}
header{text-align:center;margin-bottom:32px}
header h1{font-size:2.2rem;font-weight:700;letter-spacing:2px;
  background:linear-gradient(135deg,var(--primary),var(--accent));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}
header p{color:var(--text-dim);margin-top:4px;font-size:0.95rem}

/* Status banner */
#status{display:none;padding:12px 20px;border-radius:12px;margin-bottom:20px;
  text-align:center;font-weight:500;transition:all .3s ease}
#status.success{display:block;background:rgba(46,204,113,0.15);border:1px solid rgba(46,204,113,0.3);color:var(--success)}
#status.error{display:block;background:rgba(231,76,60,0.15);border:1px solid rgba(231,76,60,0.3);color:var(--danger)}
#status.info{display:block;background:rgba(0,122,204,0.15);border:1px solid rgba(0,122,204,0.3);color:var(--accent)}

/* Device grid */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;margin-bottom:20px}
.card{
  background:var(--glass-bg);border:1px solid var(--glass-border);
  backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
  border-radius:16px;padding:20px;transition:transform .2s,border-color .2s;
}
.card:hover{transform:translateY(-2px);border-color:rgba(0,212,255,0.35)}
.card h3{font-size:1.1rem;margin-bottom:8px;color:#fff}
.card .mac{font-family:'Courier New',monospace;color:var(--accent);font-size:0.9rem}
.card .broadcast{color:var(--text-dim);font-size:0.85rem;margin-top:2px}
.card .desc{color:var(--text-dim);font-size:0.85rem;margin-top:6px;font-style:italic}
.card-actions{display:flex;gap:8px;margin-top:16px;align-items:center}

/* Buttons */
.btn{
  border:none;border-radius:10px;padding:10px 20px;cursor:pointer;
  font-weight:600;font-size:0.9rem;transition:all .2s;
}
.btn-wake{
  background:linear-gradient(135deg,var(--primary),var(--accent));
  color:#fff;flex:1;
}
.btn-wake:hover{filter:brightness(1.15);transform:scale(1.02)}
.btn-wake:active{transform:scale(0.98)}
.btn-edit{background:rgba(255,255,255,0.08);color:var(--text);padding:10px 14px}
.btn-edit:hover{background:rgba(255,255,255,0.15)}
.btn-delete{background:rgba(231,76,60,0.15);color:var(--danger);padding:10px 14px}
.btn-delete:hover{background:rgba(231,76,60,0.3)}
.btn-add{
  background:var(--glass-bg);border:2px dashed var(--glass-border);
  color:var(--accent);width:100%;padding:16px;border-radius:16px;
  cursor:pointer;font-size:1rem;font-weight:500;transition:all .2s;
}
.btn-add:hover{border-color:var(--accent);background:rgba(0,212,255,0.05)}

/* Modal */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);
  z-index:100;align-items:center;justify-content:center;backdrop-filter:blur(4px)}
.modal-overlay.active{display:flex}
.modal{
  background:#12121a;border:1px solid var(--glass-border);border-radius:20px;
  padding:28px;width:90%;max-width:440px;
}
.modal h2{margin-bottom:20px;font-size:1.3rem;
  background:linear-gradient(135deg,var(--primary),var(--accent));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}
.form-group{margin-bottom:16px}
.form-group label{display:block;margin-bottom:6px;color:var(--text-dim);font-size:0.85rem;font-weight:500}
.form-group input,.form-group textarea{
  width:100%;padding:10px 14px;background:rgba(255,255,255,0.06);
  border:1px solid rgba(255,255,255,0.1);border-radius:10px;
  color:var(--text);font-size:0.95rem;outline:none;transition:border-color .2s;
}
.form-group input:focus,.form-group textarea:focus{border-color:var(--accent)}
.form-group textarea{resize:vertical;min-height:60px;font-family:inherit}
.form-group .hint{font-size:0.75rem;color:var(--text-dim);margin-top:4px}
.modal-actions{display:flex;gap:10px;margin-top:24px}
.btn-save{background:linear-gradient(135deg,var(--primary),var(--accent));color:#fff;flex:1}
.btn-save:hover{filter:brightness(1.15)}
.btn-cancel{background:rgba(255,255,255,0.08);color:var(--text);flex:1}
.btn-cancel:hover{background:rgba(255,255,255,0.15)}

/* Empty state */
.empty{text-align:center;padding:40px;color:var(--text-dim)}
.empty h3{font-size:1.2rem;margin-bottom:8px;color:var(--text)}

/* Footer */
footer{text-align:center;margin-top:32px;color:var(--text-dim);font-size:0.8rem}
footer a{color:var(--accent);text-decoration:none}
footer a:hover{text-decoration:underline}

/* Responsive */
@media(max-width:400px){
  body{padding:12px}
  .card{padding:16px}
  .modal{padding:20px;width:95%}
  header h1{font-size:1.8rem}
}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>PiKnock</h1>
    <p>Wake-on-LAN Controller</p>
  </header>

  <div id="status"></div>
  <div id="device-grid" class="grid"></div>
  <button class="btn-add" onclick="showModal()">+ Add Device</button>

  <footer>
    <p>Powered by <a href="https://github.com/SynapticaSolution/piknock" target="_blank">PiKnock</a>
    &mdash; Made by <a href="https://www.synaptica-solution.com" target="_blank">Synaptica</a></p>
  </footer>
</div>

<!-- Modal -->
<div class="modal-overlay" id="modal-overlay" onclick="if(event.target===this)closeModal()">
  <div class="modal">
    <h2 id="modal-title">Add Device</h2>
    <input type="hidden" id="device-id">
    <div class="form-group">
      <label for="device-name">Device Name</label>
      <input type="text" id="device-name" placeholder="e.g. My Desktop PC" maxlength="50">
    </div>
    <div class="form-group">
      <label for="device-mac">MAC Address</label>
      <input type="text" id="device-mac" placeholder="AA:BB:CC:DD:EE:FF" maxlength="17">
      <div class="hint">Format: AA:BB:CC:DD:EE:FF</div>
    </div>
    <div class="form-group">
      <label for="device-broadcast">Broadcast Address</label>
      <input type="text" id="device-broadcast" placeholder="192.168.1.255" maxlength="15">
      <div class="hint">Use 192.168.x.255 for LAN, 10.0.0.255 for direct Ethernet</div>
    </div>
    <div class="form-group">
      <label for="device-desc">Description (optional)</label>
      <textarea id="device-desc" placeholder="e.g. Main desktop on LAN" maxlength="200"></textarea>
    </div>
    <div class="modal-actions">
      <button class="btn btn-cancel" onclick="closeModal()">Cancel</button>
      <button class="btn btn-save" onclick="saveDevice()">Save</button>
    </div>
  </div>
</div>

<script>
let devices = [];

async function loadDevices() {
  try {
    const res = await fetch('/api/devices');
    devices = await res.json();
    renderDevices();
  } catch (e) {
    showStatus('Failed to load devices', 'error');
  }
}

function renderDevices() {
  const grid = document.getElementById('device-grid');
  if (devices.length === 0) {
    grid.innerHTML = '<div class="empty"><h3>No devices configured</h3><p>Add a device to get started</p></div>';
    return;
  }
  grid.innerHTML = devices.map(d => `
    <div class="card">
      <h3>${esc(d.name)}</h3>
      <div class="mac">${esc(d.mac)}</div>
      <div class="broadcast">Broadcast: ${esc(d.broadcast)}</div>
      ${d.description ? `<div class="desc">${esc(d.description)}</div>` : ''}
      <div class="card-actions">
        <button class="btn btn-wake" onclick="wakeDevice('${d.id}')">Wake</button>
        <button class="btn btn-edit" onclick="editDevice('${d.id}')">Edit</button>
        <button class="btn btn-delete" onclick="deleteDevice('${d.id}')">Del</button>
      </div>
    </div>
  `).join('');
}

async function wakeDevice(id) {
  const device = devices.find(d => d.id === id);
  if (!device) return;
  showStatus(`Sending magic packet to ${device.name}...`, 'info');
  try {
    const res = await fetch(`/api/wake/${id}`, {method: 'POST'});
    const data = await res.json();
    if (data.success) {
      showStatus(`Magic packet sent to ${device.name} via ${data.methods.join(', ')}`, 'success');
    } else {
      showStatus(`Failed: ${data.errors.join('; ')}`, 'error');
    }
  } catch (e) {
    showStatus('Request failed', 'error');
  }
}

function showModal(id) {
  const overlay = document.getElementById('modal-overlay');
  document.getElementById('modal-title').textContent = id ? 'Edit Device' : 'Add Device';
  if (id) {
    const d = devices.find(x => x.id === id);
    document.getElementById('device-id').value = d.id;
    document.getElementById('device-name').value = d.name;
    document.getElementById('device-mac').value = d.mac;
    document.getElementById('device-broadcast').value = d.broadcast;
    document.getElementById('device-desc').value = d.description || '';
  } else {
    document.getElementById('device-id').value = '';
    document.getElementById('device-name').value = '';
    document.getElementById('device-mac').value = '';
    document.getElementById('device-broadcast').value = '';
    document.getElementById('device-desc').value = '';
  }
  overlay.classList.add('active');
  document.getElementById('device-name').focus();
}

function editDevice(id) { showModal(id); }

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('active');
}

async function saveDevice() {
  const id = document.getElementById('device-id').value;
  const data = {
    name: document.getElementById('device-name').value.trim(),
    mac: document.getElementById('device-mac').value.trim().toUpperCase().replace(/-/g, ':'),
    broadcast: document.getElementById('device-broadcast').value.trim(),
    description: document.getElementById('device-desc').value.trim()
  };

  if (!data.name) { showStatus('Device name is required', 'error'); return; }
  if (!/^([0-9A-F]{2}:){5}[0-9A-F]{2}$/.test(data.mac)) {
    showStatus('Invalid MAC address format', 'error'); return;
  }
  if (!data.broadcast) { showStatus('Broadcast address is required', 'error'); return; }

  try {
    let res;
    if (id) {
      res = await fetch(`/api/devices/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
      });
    } else {
      res = await fetch('/api/devices', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
      });
    }
    if (res.ok) {
      closeModal();
      await loadDevices();
      showStatus(id ? 'Device updated' : 'Device added', 'success');
    } else {
      const err = await res.json();
      showStatus(err.error || 'Failed to save', 'error');
    }
  } catch (e) {
    showStatus('Request failed', 'error');
  }
}

async function deleteDevice(id) {
  const device = devices.find(d => d.id === id);
  if (!confirm(`Delete "${device.name}"?`)) return;
  try {
    const res = await fetch(`/api/devices/${id}`, {method: 'DELETE'});
    if (res.ok) {
      await loadDevices();
      showStatus('Device removed', 'success');
    }
  } catch (e) {
    showStatus('Request failed', 'error');
  }
}

function showStatus(msg, type) {
  const el = document.getElementById('status');
  el.textContent = msg;
  el.className = type;
  if (type === 'success' || type === 'info') {
    setTimeout(() => { el.className = ''; }, 5000);
  }
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

// Auto-format MAC address input
document.getElementById('device-mac').addEventListener('input', function(e) {
  let v = this.value.replace(/[^0-9A-Fa-f]/g, '').toUpperCase();
  let formatted = '';
  for (let i = 0; i < v.length && i < 12; i++) {
    if (i > 0 && i % 2 === 0) formatted += ':';
    formatted += v[i];
  }
  this.value = formatted;
});

// Close modal on Escape
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});

// Init
loadDevices();
</script>
</body>
</html>"""

# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------


class PiKnockHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"[PiKnock] {self.address_string()} - {format % args}")

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return None
        return json.loads(self.rfile.read(length))

    # -- GET routes ---------------------------------------------------------

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path == "/":
            body = HTML_PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/api/devices":
            config = load_config()
            self.send_json(config.get("devices", []))

        elif path == "/api/status":
            self.send_json(
                {
                    "wakeonlan_available": check_wakeonlan(),
                    "version": "1.0.0",
                }
            )

        else:
            self.send_json({"error": "Not found"}, 404)

    # -- POST routes --------------------------------------------------------

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path

        # Wake a device
        if path.startswith("/api/wake/"):
            device_id = path[len("/api/wake/") :]
            config = load_config()
            device = next((d for d in config["devices"] if d["id"] == device_id), None)
            if not device:
                self.send_json({"error": "Device not found"}, 404)
                return
            result = send_wol(device["mac"], device["broadcast"])
            self.send_json(result)
            return

        # Add a device
        if path == "/api/devices":
            data = self.read_json_body()
            if not data:
                self.send_json({"error": "Empty request body"}, 400)
                return

            mac = normalize_mac(data.get("mac", ""))
            if not mac:
                self.send_json({"error": "Invalid MAC address"}, 400)
                return
            if not data.get("name", "").strip():
                self.send_json({"error": "Name is required"}, 400)
                return
            if not data.get("broadcast", "").strip():
                self.send_json({"error": "Broadcast address is required"}, 400)
                return

            config = load_config()
            device = {
                "id": str(uuid.uuid4())[:8],
                "name": data["name"].strip(),
                "mac": mac,
                "broadcast": data["broadcast"].strip(),
                "description": data.get("description", "").strip(),
            }
            config["devices"].append(device)
            save_config(config)
            self.send_json(device, 201)
            return

        self.send_json({"error": "Not found"}, 404)

    # -- PUT routes ---------------------------------------------------------

    def do_PUT(self):
        path = urllib.parse.urlparse(self.path).path

        if path.startswith("/api/devices/"):
            device_id = path[len("/api/devices/") :]
            data = self.read_json_body()
            if not data:
                self.send_json({"error": "Empty request body"}, 400)
                return

            mac = normalize_mac(data.get("mac", ""))
            if not mac:
                self.send_json({"error": "Invalid MAC address"}, 400)
                return

            config = load_config()
            for i, d in enumerate(config["devices"]):
                if d["id"] == device_id:
                    config["devices"][i] = {
                        "id": device_id,
                        "name": data.get("name", d["name"]).strip(),
                        "mac": mac,
                        "broadcast": data.get("broadcast", d["broadcast"]).strip(),
                        "description": data.get("description", "").strip(),
                    }
                    save_config(config)
                    self.send_json(config["devices"][i])
                    return

            self.send_json({"error": "Device not found"}, 404)
            return

        self.send_json({"error": "Not found"}, 404)

    # -- DELETE routes ------------------------------------------------------

    def do_DELETE(self):
        path = urllib.parse.urlparse(self.path).path

        if path.startswith("/api/devices/"):
            device_id = path[len("/api/devices/") :]
            config = load_config()
            original_len = len(config["devices"])
            config["devices"] = [d for d in config["devices"] if d["id"] != device_id]
            if len(config["devices"]) == original_len:
                self.send_json({"error": "Device not found"}, 404)
                return
            save_config(config)
            self.send_json({"ok": True})
            return

        self.send_json({"error": "Not found"}, 404)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    config = load_config()
    host = config.get("server", {}).get("host", "0.0.0.0")
    port = config.get("server", {}).get("port", 8080)

    if not check_wakeonlan():
        print(
            "[PiKnock] WARNING: 'wakeonlan' is not installed. Install it with: sudo apt install wakeonlan"
        )

    server = ThreadingHTTPServer((host, port), PiKnockHandler)
    print(f"[PiKnock] Server running on http://{host}:{port}")
    print(f"[PiKnock] Config file: {CONFIG_FILE}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[PiKnock] Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
