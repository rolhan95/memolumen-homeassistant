# Lumora für Home Assistant

Integration für [Home Assistant](https://www.home-assistant.io/), die einen **Lumora-Bilderrahmen** (digitaler Bilderrahmen für Windows-Tablets) direkt einbindet – ohne MQTT-Broker. Installation über [HACS](https://hacs.xyz/).

*English summary below.*

## Voraussetzungen

- Lumora **2.3.0 oder neuer** auf dem Tablet
- Home Assistant **2025.3** oder neuer, HACS
- Adresse der Lumora-Weboberfläche (z. B. `https://192.168.1.50:8443`) und der **API-Token** aus Lumora (*Home Assistant → Steuerung per REST*)

## Installation

1. In Home Assistant **HACS → ⋮ → Benutzerdefinierte Repositories** öffnen.
2. `https://github.com/rolhan95/lumora-homeassistant` eintragen, Typ **Integration**, hinzufügen.
3. **Lumora** in HACS suchen, herunterladen und Home Assistant neu starten.
4. **Einstellungen → Geräte & Dienste → Integration hinzufügen → Lumora**.
5. Adresse und API-Token eintragen. „Zertifikat prüfen“ ausgeschaltet lassen, solange Lumora seine eigene lokale Zertifizierungsstelle verwendet.

Ohne HACS: den Ordner `custom_components/lumora` nach `config/custom_components/` in Home Assistant kopieren und Home Assistant neu starten.

> MQTT in Lumora und diese Integration nicht gleichzeitig nutzen – sonst erscheint der Rahmen doppelt.

## Funktionen

| Art | Entitäten |
|---|---|
| Schalter | Bildschirm, Abwesenheitsmodus, Zeitplan |
| Zahl | Helligkeit (0–100 %) |
| Sensoren | Umgebungslicht, Anzahl Fotos, nächstes Einschalten, Version |
| Bewegung | Bewegungsmelder der Kamera (wenn in Lumora aktiviert) |
| Tasten | nächstes/vorheriges Foto, Diashow anhalten/fortsetzen, Einblendung schließen, App neu starten |
| Benachrichtigung | Nachricht als Banner auf dem Rahmen (`notify.send_message`) |

**Aktionen:** `lumora.show_camera` (Kamera einblenden), `lumora.show_image` (Bild einblenden), `lumora.notify` (Nachricht anzeigen), `lumora.dismiss` (Einblendung schließen), `lumora.display_on_for` (Bildschirm vorübergehend einschalten). Ohne Angabe eines Geräts gelten sie für alle Lumora-Rahmen.

## Bewegungsmelder im Raum

Unter **Einstellungen → Geräte & Dienste → Lumora → Konfigurieren → Bewegungsmelder im Raum** wählst du einen oder mehrere Bewegungs- oder Präsenzmelder (Binärsensoren) aus dem Raum, in dem der Rahmen steht. Meldet einer Bewegung, wendet Lumora die Regeln aus seinem Reiter *Bewegung* an: nachts bei Bewegung einschalten, wie lange an bleiben, tagsüber ausschalten, wenn längere Zeit keine Bewegung war. Die Kamera am Tablet muss dafür nicht eingeschaltet sein. Bleibt ein Melder auf „an“ (Präsenz), wird die Bewegung jede Minute erneut gemeldet. Die eigenen Entitäten des Rahmens werden nicht angeboten (keine Rückkopplung).

Benötigt **Lumora 2.3.2** oder neuer. Feld leeren oder Integration entfernen hebt die Kopplung in Lumora wieder auf.

## Türklingel

Unter **Einstellungen → Geräte & Dienste → Lumora → Konfigurieren** wählst du:

| Feld | Bedeutung |
|---|---|
| Auslöser (Türklingel) | eine oder mehrere Entitäten: Binärsensor (zählt beim Wechsel auf „an“), Ereignis-Entität, Taste, `input_boolean`, Schalter |
| Kamera | diese Kamera wird beim Klingeln eingeblendet |
| Anzeigedauer | Standard 60 s |
| Titel / Untertitel | Text der Einblendung, z. B. „Es klingelt an der Haustür“ |
| Sperrzeit | weitere Auslösungen in dieser Zeit werden ignoriert (Standard 10 s) |

### Klingel per Webhook (z. B. Shelly)

Alternativ oder zusätzlich zu den Entitäten kann ein Gerät im Heimnetz die Klingel über einen Webhook auslösen:

1. In den Optionen **Klingel per Webhook** einschalten. Die **Webhook-ID** ist mit einer zufälligen ID vorbelegt und frei änderbar (Buchstaben, Ziffern, `-`, `_`).
2. Nach dem Speichern erscheint die Adresse als Benachrichtigung in Home Assistant (und beim nächsten Öffnen oben im Optionsdialog), z. B. `http://homeassistant.local:8123/api/webhook/<ID>`.
3. Im Shelly eintragen:
   - **Shelly Plus/Pro/Gen3/Gen4:** Weboberfläche → Actions → neue Aktion → Auslöser „Input toggled on“ bzw. „Button push“ → Webhook/URL aufrufen.
   - **Shelly Gen1:** Settings → I/O URL actions → „Button switched ON url“ bzw. „Button short press url“.

Der Webhook nimmt GET und POST an, nur aus dem Heimnetz, und beachtet die Sperrzeit. Ist im Shelly schon eine Webhook-Adresse aus einer eigenen Automation eingetragen, kannst du deren ID übernehmen – die Automation vorher deaktivieren, sonst meldet der Dialog „Webhook-ID wird schon verwendet“.

Danach erscheint am Gerät die Taste **Türklingel testen**. Wechsel von „nicht verfügbar“ (z. B. nach einem Neustart des Klingelmoduls) lösen nicht aus. Eine eigene Automation für die Klingel ist damit nicht mehr nötig – nutzt du schon eine, eine von beiden abschalten, sonst wird die Kamera doppelt angefordert.

## Aktion im eigenen Skript

Beispiel – Türkamera beim Klingeln per Automation:

```yaml
action: lumora.show_camera
data:
  camera: camera.haustuer
  duration: 45
  title: Es klingelt
```

Damit Lumora das Kamerabild abrufen kann, müssen in Lumora unter *Home Assistant → Verbindung zu Home Assistant* die Adresse von Home Assistant und ein langlebiges Zugriffstoken eingetragen sein.

Ändert sich der API-Token in Lumora, fordert Home Assistant zur erneuten Anmeldung auf.

## Teststand

Getestet sind die Lumora-Schnittstellen, die die Integration aufruft (Status, Anzeige, Abwesenheit, Zeitplan, Helligkeit, Befehle, Benachrichtigung, Abweisung eines falschen Tokens) – mit Lumora 2.3.0 auf einem Testrechner.

In einem echten Home Assistant (2026.11) mit Lumora 2.3.0 auf einem Windows-Tablet: Installation über HACS (1.2.0, Update auf 1.3.1), Einrichtung mit Adresse und API-Token, Entitäten liefern Werte (Bildschirm, Version, Helligkeit, Sensoren). Der Optionsdialog mit Türklingel-Sensor, Webhook-ID, Kamera und Bewegungsmelder speichert in einem Schritt; die Prüfung „Webhook-ID schon belegt“ greift, solange eine Automation dieselbe ID nutzt. Die Taste „Türklingel testen“ blendet das Live-Bild der Eingangskamera auf dem Rahmen ein. Mit Lumora 2.3.0 meldet die Integration erwartungsgemäß, dass der Bewegungsmelder Lumora 2.3.2 braucht.

**Noch nicht getestet:** echtes Klingeln über Sensor und Shelly-Webhook, Bewegungsmelder mit Lumora ab 2.3.2, erneute Anmeldung bei geändertem Token.

---

## English

Home Assistant integration for the **Lumora** picture frame app (requires Lumora 2.3.0+). Install via HACS → Custom repositories → `https://github.com/rolhan95/lumora-homeassistant` (type *Integration*), restart Home Assistant, then add the **Lumora** integration with the frame address (e.g. `https://192.168.1.50:8443`) and the API token shown in Lumora under *Home Assistant → Control via REST*. Motion: pair one or more motion/presence sensors of the room (requires Lumora 2.3.2+); Lumora then applies its motion rules without the tablet camera. Doorbell: in the integration options pick one or more trigger entities and/or a webhook (e.g. for a Shelly) and a camera – the frame then shows the camera when the doorbell rings (with a test button). Provides switches (screen, away mode, schedule), brightness, sensors, motion, buttons, a notify entity and the actions `lumora.show_camera`, `lumora.show_image`, `lumora.notify`, `lumora.dismiss`, `lumora.display_on_for`.

Status: the Lumora API endpoints used by the integration are tested; the integration itself has not yet been tested in a running Home Assistant.

## Lizenz

MIT – © 2026 Suderland IT
