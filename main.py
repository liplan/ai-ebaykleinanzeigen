# version: v1.8 - 2025-06-25

import os
import json
from dotenv import load_dotenv
from datetime import datetime
from PIL import Image
import pillow_heif
import pytesseract
from rich import print
from rich.prompt import Prompt
import openai
import requests
from bs4 import BeautifulSoup
import statistics
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementNotInteractableException,
    StaleElementReferenceException,
)
import subprocess
import time

# 🧪 Konfiguration
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

HOTFOLDER = "hotfolder"
LOGCSV = "upload_log.csv"
LOGJSON = "upload_log.json"

# Chrome-Konfiguration
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHROME_PROFILE = os.path.expanduser("~/.chrome-ignorecert-profile")
CHROME_PORT = 9222

# 📁 Logdateien anlegen
if not os.path.exists(LOGCSV):
    with open(LOGCSV, "w") as f:
        f.write("Zeitpunkt;Titel;Preis;Kategorie;Zustand;Beschreibung\n")

if not os.path.exists(LOGJSON):
    with open(LOGJSON, "w") as f:
        json.dump([], f)

def log_csv(eintrag):
    with open(LOGCSV, "a") as f:
        f.write(f"{eintrag['zeitpunkt']};{eintrag['titel']};{eintrag['preis']}€;{eintrag['kategorie']};{eintrag['zustand']};{eintrag['beschreibung'].replace(';', ',')}\n")

def log_json(eintrag):
    with open(LOGJSON, "r+") as f:
        daten = json.load(f)
        daten.append(eintrag)
        f.seek(0)
        json.dump(daten, f, indent=2)

def konvertiere_heic_bilder(ordner):
    for datei in os.listdir(ordner):
        if datei.lower().endswith(".heic"):
            pfad = os.path.join(ordner, datei)
            try:
                if os.path.getsize(pfad) < 1024:
                    print(f"[yellow]⚠️ Überspringe beschädigte HEIC-Datei: {datei}[/yellow]")
                    continue
                heif = pillow_heif.read_heif(pfad)
                bild = Image.frombytes(heif.mode, heif.size, heif.data, "raw")
                ziel = pfad.rsplit(".", 1)[0] + ".jpg"
                bild.save(ziel, format="JPEG")
                os.remove(pfad)
                print(f"[blue]➤ Konvertiert: {datei} → {os.path.basename(ziel)}[/blue]")
            except Exception as e:
                print(f"[red]❌ Fehler bei {datei}:[/red] {e}")

def extrahiere_text_aus_bildern(ordner):
    texte = []
    for datei in os.listdir(ordner):
        if datei.lower().endswith((".jpg", ".jpeg", ".png")):
            pfad = os.path.join(ordner, datei)
            print(f"[cyan]🔍 Texterkennung: {pfad}[/cyan]")
            try:
                bild = Image.open(pfad)
                text = pytesseract.image_to_string(bild)
                if text.strip():
                    texte.append(text.strip())
            except Exception as e:
                print(f"[red]❌ Texterkennung fehlgeschlagen: {e}[/red]")
    return "\n".join(texte)

def gpt_titel_und_beschreibung(produktordner, ocr_text):
    prompt = f"""
    Erstelle einen eBay Kleinanzeigen-Titel (max. 50 Zeichen) und eine ansprechende Beschreibung.

    Produktordnername: {produktordner}
    Erkannter Text auf Bildern:
    {ocr_text}

    Antwort im JSON-Format: {{"titel": "...", "beschreibung": "..."}}"""
    try:
        res = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return json.loads(res.choices[0].message.content.strip())
    except Exception as e:
        print(f"[red]GPT-Fehler:[/red] {e}")
        return {"titel": produktordner.replace("_", " "), "beschreibung": ocr_text}

def gpt_kategorie_vorschlag(textbasis):
    prompt = f"""
    Ordne folgendem eBay-Kleinanzeigen-Inhalt eine passende Haupt- und Unterkategorie zu.
    Gib zurück: Hauptkategorie > Unterkategorie

    Inhalt:
    {textbasis}"""
    try:
        res = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        print(f"[red]⚠️ GPT-Kategoriefehler:[/red] {e}")
        return "Allgemein > Sonstiges"

def ermittle_durchschnittspreis(suchbegriff):
    url = f"https://www.kleinanzeigen.de/s-suche.html?keywords={suchbegriff}"
    try:
        html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text
        soup = BeautifulSoup(html, "html.parser")
        preise = []
        for eintrag in soup.select("article .aditem-main--middle .aditem-main--top--right")[:5]:
            text = eintrag.get_text(strip=True).replace(".", "").replace("€", "").strip()
            if text.isdigit():
                preise.append(int(text))
        if preise:
            avg = int(statistics.mean(preise))
            print(f"💰 Durchschnittspreis (aus {len(preise)}): {avg} €")
            return avg
        else:
            print("[yellow]⚠️ Keine Preise gefunden.[/yellow]")
            return 0
    except Exception as e:
        print(f"[red]❌ Fehler bei Preisrecherche:[/red] {e}")
        return 0

def frage_zustand():
    return Prompt.ask("Zustand [neu/wie neu/gut/gebraucht/defekt]", default="gebraucht").strip().lower()

def prüfe_chrome_debug_session():
    try:
        res = requests.get(f"http://localhost:{CHROME_PORT}/json/version", timeout=2)
        if res.status_code == 200:
            print("[green]🟢 Chrome-Debugging-Schnittstelle erreichbar[/green]")
            return True
        else:
            print(f"[red]⚠️ Chrome-Debugging antwortet nicht (Status {res.status_code})[/red]")
            return False
    except Exception as e:
        print(f"[red]❌ Kann keine Verbindung zu Chrome-Debugging aufbauen:[/red] {e}")
        return False

def starte_chrome_debugging():
    """Starte Chrome im Debug-Modus, falls er noch nicht läuft."""
    if prüfe_chrome_debug_session():
        return True

    if not os.path.exists(CHROME_PATH):
        print(f"[red]❌ Chrome nicht gefunden unter {CHROME_PATH}[/red]")
        return False

    cmd = [
        CHROME_PATH,
        f"--remote-debugging-port={CHROME_PORT}",
        f"--user-data-dir={CHROME_PROFILE}",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
    ]

    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print(f"[red]❌ Chrome nicht gefunden unter {CHROME_PATH}[/red]")
        return False

    # Warte, bis die Debug-Schnittstelle erreichbar ist (max. 10s)
    for _ in range(10):
        if prüfe_chrome_debug_session():
            return True
        time.sleep(1)

    print("[red]⚠️ Chrome-Debugging konnte nicht gestartet werden.[/red]")
    return False

def lade_bilder(driver, bilderpfad):
    bilddateien = [
        os.path.abspath(os.path.join(bilderpfad, f))
        for f in os.listdir(bilderpfad)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    if not bilddateien:
        print("[yellow]⚠️ Keine Bilder zum Hochladen gefunden.[/yellow]")
        return

    image_input = driver.find_element(By.NAME, "image1")
    try:
        image_input.send_keys("\n".join(bilddateien))
    except ElementNotInteractableException:
        print("[red]❌ Element 'image1' nicht interagierbar[/red]")
        raise

    try:
        WebDriverWait(driver, 20).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "img")) >= len(bilddateien)
        )
    except TimeoutException:
        print("[yellow]⚠️ Konnte Upload nicht bestätigen.[/yellow]")

def send_keys_stabil(driver, by, locator, text, feldname, versuche=3):
    """Sende Text an ein Element und fange StaleElementReferenceException ab."""
    for i in range(versuche):
        try:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((by, locator)))
            element = driver.find_element(by, locator)
            element.send_keys(text)
            return
        except StaleElementReferenceException:
            time.sleep(0.5)
        except ElementNotInteractableException:
            print(f"[red]❌ Element '{feldname}' nicht interagierbar[/red]")
            raise
    raise Exception(f"Konnte Feld '{feldname}' nach {versuche} Versuchen nicht ausfüllen")

def führe_upload_durch(info, bilderpfad):
    print("[cyan]🌐 Starte Chrome-Debugging-Session...[/cyan]")

    if not starte_chrome_debugging():
        print("[red]Bitte starte Chrome manuell:[/red]")
        print(f'  {CHROME_PATH} --remote-debugging-port={CHROME_PORT} --user-data-dir="{CHROME_PROFILE}"')
        return

    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{CHROME_PORT}")

    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)

    try:
        driver.get("https://www.kleinanzeigen.de/p-anzeige-aufgeben-schritt2.html")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "title")))

        send_keys_stabil(driver, By.NAME, "title", info["titel"], "title")

        send_keys_stabil(driver, By.NAME, "description", info["beschreibung"], "description")

        send_keys_stabil(driver, By.NAME, "priceAmount", str(info["preis"]), "priceAmount")

        zustand_mapping = {
            "neu": "new",
            "wie neu": "mint",
            "gut": "good",
            "gebraucht": "used",
            "defekt": "defect"
        }
        zustand_key = zustand_mapping.get(info["zustand"], "used")
        zustand_element = driver.find_element(By.CSS_SELECTOR, f"label[for='condition_{zustand_key}']")
        try:
            driver.execute_script("arguments[0].click();", zustand_element)
        except ElementNotInteractableException:
            print("[red]❌ Element 'zustand' nicht interagierbar[/red]")
            raise

        lade_bilder(driver, bilderpfad)

        WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
        )
        print("[green]✔️ Upload-Felder ausgefüllt. Bitte manuell prüfen und absenden.[/green]")

    except Exception as e:
        print(f"[red]❌ Upload-Fehler:[/red] {e}")
    finally:
        driver.quit()

def main():
    print("[bold green]🚀 Starte eBay Kleinanzeigen Assistent[/bold green]")

    if not os.path.exists(HOTFOLDER):
        print(f"[red]❌ Hotfolder '{HOTFOLDER}' fehlt[/red]")
        return

    produktordner = [d for d in os.listdir(HOTFOLDER) if os.path.isdir(os.path.join(HOTFOLDER, d))]
    if not produktordner:
        print("[yellow]📭 Keine Unterordner gefunden[/yellow]")
        return

    for ordner in produktordner:
        pfad = os.path.join(HOTFOLDER, ordner)
        print(f"\n📦 Verarbeite: [bold]{ordner}[/bold]")

        konvertiere_heic_bilder(pfad)
        ocr_text = extrahiere_text_aus_bildern(pfad)
        vorschlag = gpt_titel_und_beschreibung(ordner, ocr_text)
        zustand = frage_zustand()
        kategorie = gpt_kategorie_vorschlag(vorschlag["beschreibung"])
        preis = ermittle_durchschnittspreis(vorschlag["titel"])

        zeit = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        eintrag = {
            "zeitpunkt": zeit,
            "ordner": ordner,
            "titel": vorschlag["titel"],
            "beschreibung": vorschlag["beschreibung"],
            "kategorie": kategorie,
            "zustand": zustand,
            "preis": preis
        }

        log_csv(eintrag)
        log_json(eintrag)

        print(f"\n[bold blue]🧾 Vorschau:[/bold blue]")
        print(f"[green]Titel:[/green] {eintrag['titel']}")
        print(f"[green]Beschreibung:[/green] {eintrag['beschreibung'][:200]}...")
        print(f"[green]Kategorie:[/green] {eintrag['kategorie']}")
        print(f"[green]Zustand:[/green] {eintrag['zustand']}")
        print(f"[green]Preisvorschlag:[/green] {eintrag['preis']} €")

        führe_upload_durch(eintrag, pfad)

if __name__ == "__main__":
    main()
