import csv
from statistics import mean
from collections import defaultdict

LOGFILE = 'upload_log.csv'


def parse_log(path):
    entries = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        next(reader, None)  # header
        for row in reader:
            if len(row) < 6:
                continue
            zeitpunkt, titel, preis_str, kategorie, beschreibung, link = row[:6]
            preis_digits = ''.join(ch for ch in preis_str if ch.isdigit())
            preis = int(preis_digits) if preis_digits else 0
            success = link.startswith('http')
            entries.append({'zeitpunkt': zeitpunkt, 'preis': preis,
                            'kategorie': kategorie.strip(), 'success': success})
    return entries


def main():
    entries = parse_log(LOGFILE)
    if not entries:
        print('Keine Einträge gefunden.')
        return

    total = len(entries)
    successes = sum(1 for e in entries if e['success'])
    fails = total - successes
    avg_price = mean(e['preis'] for e in entries)

    cat_counts = defaultdict(int)
    for e in entries:
        cat_counts[e['kategorie']] += 1

    print(f'Gesamtanzahl Einträge: {total}')
    print(f'Erfolgreich veröffentlicht: {successes}')
    print(f'Fehlgeschlagen: {fails}')
    print(f'Durchschnittlicher Preis: {avg_price:.2f} €')
    print('Anzeigen pro Kategorie:')
    for cat, count in cat_counts.items():
        print(f'  {cat}: {count}')


if __name__ == '__main__':
    main()
