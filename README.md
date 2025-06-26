# ai-ebaykleinanzeigen

Dieses Projekt automatisiert das Erstellen von Anzeigen bei eBay Kleinanzeigen.

## Vorbereitung
1. Alle Bilder eines Produkts in einen Unterordner von `hotfolder` legen.
2. Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```

## Ausführung
```bash
python main.py
```
Das Skript startet Chrome automatisch im Debug-Modus (Port 9222). Stelle sicher, dass Chrome unter
`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` verfügbar ist.
