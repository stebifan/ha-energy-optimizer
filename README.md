# Energy Optimizer

Home Assistant Custom Integration (HACS) für ganzheitliches Energiemanagement mit dynamischen Strompreisen, Verbrauchs-/PV-Prognose und intelligenter Akkusteuerung.

## Features (v0.2.0)

- **Strompreis:** EPEX Spot 15-Minuten-Slots aus Sensor-Attributen, inkl. Aufschlag
- **Verbrauchsprognose:** Wochentag/Stunde-Profil aus Recorder-Historie (30 Tage)
- **PV-Prognose:** Forecast Solar + optionale PV-Subentries
- **Optimizer:** Heuristik oder **Dynamic Programming** (Optionen)
- **Multi-Akku:** Prioritäts-basierte EcoFlow-Ladung (nur ein Gerät gleichzeitig)
- **Verschiebbare Lasten:** Planung in günstige/PV-Stunden, Auto-Steuerung
- **Kosten-KPI:** Baseline vs. optimiert vs. Einsparung
- **EcoFlow:** Netzladen via `backup_reserve_level` erhöhen (15-min Cooldown)
- **Victron-Puffer:** Entladung via `input_number.pv_status` / `pv_strom` (10 = 800 W)
- **Blueprints:** EcoFlow Netzladen für `signals_only` Modus
- **Dashboard:** Beispiel-Lovelace unter `dashboards/energy_optimizer.yaml`

### Roadmap

| Version | Status | Inhalt |
|---------|--------|--------|
| v0.1.0 | Fertig | Preise, Prognosen, Heuristik, Adapter, Auto-Modus |
| v0.2.0 | Fertig | Multi-Akku, Lasten, DP-Engine, KPIs, Blueprints, Dashboard |
| v0.3.0 | Geplant | Wetter in Verbrauchsprognose, Frontend Card, LP-Optimizer |

## Installation (HACS)

1. HACS → Integrations → Custom Repositories
2. Repository-URL hinzufügen (dieses Repo)
3. **Energy Optimizer** installieren
4. Home Assistant neu starten
5. Einstellungen → Geräte & Dienste → Integration hinzufügen → **Energy Optimizer**

Alternativ manuell: `custom_components/energy_optimizer` nach `/config/custom_components/` kopieren.

## Einrichtung

### Schritt 1 — Basis

| Feld | Beispiel |
|------|----------|
| Hausverbrauch Leistung | `sensor.hausleistung_gesamt` |
| Strompreis | `sensor.epex_spot_data_market_price` |
| PV Prognose heute | `sensor.energy_production_today` |
| PV Prognose morgen | `sensor.energy_production_tomorrow` |
| PV Leistung jetzt | `sensor.power_production_now` |

### Schritt 2 — Subentries (Integration → Konfigurieren)

**Batterie EcoFlow (Beispiel Büro):**

- Typ: `ecoflow`
- Kapazität kWh: z.B. `3.0`
- SOC: `sensor.buro_power_battery_soc`
- Backup Reserve: `number.buro_backup_reserve_level`

**Batterie Victron-Puffer:**

- Typ: `victron_buffer`
- Kapazität kWh: einstellbar
- SOC: Victron-Sensor
- pv_status: `input_number.pv_status`
- pv_strom: `input_number.pv_strom`

**Verschiebbare Last:**

- Schalter/Script, Priorität, Constraint `hard`/`soft`, Zeitfenster

## Optimizer-Engine

Unter **Optionen** wählbar:

| Engine | Beschreibung |
|--------|--------------|
| `heuristic` | Schnelle Heuristik (6 günstigste / teuerste Stunden) |
| `dp` | Dynamic Programming über 24h mit SOC-Modell |

## Dashboard importieren

1. Einstellungen → Dashboards → Dashboard hinzufügen → YAML
2. Inhalt aus [`dashboards/energy_optimizer.yaml`](dashboards/energy_optimizer.yaml) einfügen
3. Entity-IDs an deine Installation anpassen

## Blueprints (signals_only)

Blueprints liegen unter `blueprints/automation/` — in HA unter Blueprints importieren.

| Service | Beschreibung |
|---------|--------------|
| `energy_optimizer.recalculate` | Plan neu berechnen |
| `energy_optimizer.apply_plan` | Plan manuell anwenden |
| `energy_optimizer.set_profile` | Profil wechseln |

## Entwicklung

```bash
cd energy_optimizer
python -m pytest tests/ -q
```

## Architektur

Siehe Plan-Dokumentation im Projekt-Repository.

## Lizenz

MIT
