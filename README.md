# ai-ebaykleinanzeigen

Dieses Projekt automatisiert das Erstellen von Anzeigen bei Kleinanzeigen (ehemals eBay Kleinanzeigen).

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
Das Skript startet Chrome automatisch im Debug-Modus (Port 9222). Stelle sicher,
 dass Chrome unter `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` verfügbar ist.

## Log-Analyse
Nach dem Ausführen werden Einträge in `upload_log.csv` gespeichert. Mit
`analyze_logs.py` lässt sich daraus eine Zusammenfassung erstellen:
```bash
python analyze_logs.py
```
