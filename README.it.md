# PiKnock

> *Toc toc... sveglia!* Un controller Wake-on-LAN con interfaccia web, progettato per Raspberry Pi.

**[English](README.md)** | **[Italiano](README.it.md)**

Accendi i tuoi PC da remoto tramite browser — funziona sulla rete LAN o con un cavo Ethernet diretto tra Pi e PC.

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.7+-green)
![Dependencies](https://img.shields.io/badge/dipendenze-zero-brightgreen)

## Funzionalita'

- **Gestione dispositivi via web** — aggiungi, modifica, rimuovi i PC target dal browser
- **WOL multi-metodo** — invia magic packet su piu' indirizzi broadcast per affidabilita'
- **Supporto Ethernet diretto** — accendi un PC collegato direttamente al Pi senza router
- **Zero dipendenze Python** — usa solo la libreria standard
- **Server in un singolo file** — un file Python, facile da installare e mantenere
- **REST API** — automatizza con `curl` o script
- **UI responsiva** — funziona su desktop e mobile

## Come Funziona

PiKnock avvia un server HTTP leggero sul Raspberry Pi. Quando clicchi "Wake" nell'interfaccia web, invia [magic packet Wake-on-LAN](https://it.wikipedia.org/wiki/Wake-on-LAN) alla scheda di rete del PC target, che si accende.

**Due scenari di rete supportati:**

```
Scenario 1: LAN (via router)                Scenario 2: Ethernet diretto
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

## Requisiti

- Raspberry Pi (qualsiasi modello) con Python 3.7+
- Pacchetto `wakeonlan`: `sudo apt install wakeonlan`
- PC target con WOL abilitato nel BIOS

## Installazione Rapida

```bash
git clone https://github.com/SynapticaSolution/piknock.git
cd piknock
sudo ./install.sh
```

L'installer:
1. Installa `wakeonlan`
2. Copia PiKnock in `/opt/piknock`
3. Configura un servizio systemd (avvio automatico al boot)
4. Opzionalmente configura la connessione Ethernet diretta

## Installazione Manuale

```bash
# Installa la dipendenza
sudo apt install wakeonlan

# Copia i file
sudo mkdir -p /opt/piknock
sudo cp piknock.py /opt/piknock/
sudo cp config.example.json /opt/piknock/config.json

# Avvia
python3 /opt/piknock/piknock.py
```

## Aggiornamento

```bash
cd piknock
git pull
sudo cp piknock.py /opt/piknock/
sudo systemctl restart piknock
```

## Sviluppo

```bash
cp config.example.json config.json
python3 piknock.py
# Apri http://localhost:8080
```

## Configurazione

I dispositivi sono salvati in `config.json`:

```json
{
  "devices": [
    {
      "id": "abc123",
      "name": "Il mio Desktop",
      "mac": "AA:BB:CC:DD:EE:FF",
      "broadcast": "192.168.1.255",
      "description": "PC principale sulla LAN"
    }
  ],
  "server": {
    "port": 8080,
    "host": "0.0.0.0"
  }
}
```

Puoi modificare questo file direttamente o usare l'interfaccia web.

## Configurazione Ethernet Diretto

Per accendere un PC collegato direttamente al Pi (senza router):

**Sul Raspberry Pi** (gestito da `install.sh`):
- Imposta `eth0` con IP statico `10.0.0.1/24`

**Sul PC target**:
- Imposta l'interfaccia Ethernet con IP statico `10.0.0.2`, subnet `255.255.255.0`, nessun gateway

Poi aggiungi il dispositivo in PiKnock con indirizzo broadcast `10.0.0.255`.

## Configurazione BIOS per WOL

Abilita queste opzioni nel BIOS del PC target:
- **Wake on LAN**: Abilitato
- **Wake on PCIe/PCI**: Abilitato
- **ERP Support**: Disabilitato
- **Deep Sleep**: Disabilitato

## API

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| `GET` | `/api/devices` | Lista tutti i dispositivi |
| `POST` | `/api/devices` | Aggiungi un dispositivo |
| `PUT` | `/api/devices/{id}` | Modifica un dispositivo |
| `DELETE` | `/api/devices/{id}` | Rimuovi un dispositivo |
| `POST` | `/api/wake/{id}` | Invia WOL al dispositivo |
| `GET` | `/api/status` | Info server |

**Esempio:**
```bash
# Accendi un dispositivo
curl -X POST http://raspberrypi:8080/api/wake/abc123

# Aggiungi un dispositivo
curl -X POST http://raspberrypi:8080/api/devices \
  -H "Content-Type: application/json" \
  -d '{"name":"Server","mac":"AA:BB:CC:DD:EE:FF","broadcast":"192.168.1.255"}'
```

## Licenza

MIT - Vedi [LICENSE](LICENSE)

---

Creato da [Synaptica](https://www.synaptica-solution.com)
