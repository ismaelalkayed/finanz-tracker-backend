# Finanz-Tracker

Eine Webanwendung zum Erfassen und Auswerten privater Ausgaben. Eingaben landen in
einer PostgreSQL-Datenbank in der Cloud und sind von jedem Gerät aus erreichbar.

**Oberfläche:** https://ismaelalkayed.github.io/finanz-tracker-backend/
**API-Dokumentation:** https://finanz-tracker-backend-3knj.onrender.com/docs

Der erste Aufruf kann bis zu einer Minute dauern: Das Backend läuft auf einem
kostenlosen Tarif und wird bei Inaktivität pausiert.

## Funktionen

- Ausgaben mit Betrag, Datum, Kategorie und optionaler Notiz erfassen
- Einträge nachträglich bearbeiten oder löschen
- Nach Kategorie filtern
- Monatsauswertung mit Summe und Anzahl je Kategorie

## Aufbau

Die Anwendung besteht aus drei getrennten Schichten:

| Schicht | Technologie | Gehostet bei |
|---|---|---|
| Oberfläche | HTML, CSS, JavaScript (ohne Framework) | GitHub Pages |
| API | Python, FastAPI, SQLModel | Render |
| Datenbank | PostgreSQL | Neon |

Die Trennung bedeutet: Jede Schicht ist austauschbar, ohne die anderen anzufassen.
Eine native App könnte dieselbe API ansprechen wie die Weboberfläche.

## API

| Methode | Pfad | Zweck |
|---|---|---|
| `GET` | `/expenses` | Alle Ausgaben, optional `?kategorie=Name` |
| `POST` | `/expenses` | Neue Ausgabe anlegen |
| `PUT` | `/expenses/{id}` | Ausgabe ändern |
| `DELETE` | `/expenses/{id}` | Ausgabe löschen |
| `GET` | `/summary` | Summen je Kategorie, optional `?monat=JJJJ-MM` |

Die Gruppierung in `/summary` passiert per `GROUP BY` in der Datenbank, nicht in Python.

## Lokal starten

```bash
git clone https://github.com/ismaelalkayed/finanz-tracker-backend.git
cd finanz-tracker-backend

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Eine Datei `.env` im Projektordner anlegen:

```
DATABASE_URL=postgresql://benutzer:passwort@host/datenbank
```

Ohne diese Datei fällt die Anwendung auf eine lokale SQLite-Datei zurück, läuft also
auch ohne Datenbankzugang. Die `.env` steht in der `.gitignore` und gehört niemals
ins Repository.

Starten:

```bash
uvicorn main:app --reload
```

Danach ist die API unter http://localhost:8000 erreichbar, die interaktive
Dokumentation unter http://localhost:8000/docs.

Für die Oberfläche in `index.html` die Konstante `API` oben im Skript-Teil auf
`http://localhost:8000` umstellen und die Datei im Browser öffnen.

## Tests

```bash
pytest -v
```

17 Tests decken alle Endpunkte ab, jeweils den Normal- und den Fehlerfall. Sie laufen
gegen eine temporäre SQLite-Datei: `test_main.py` setzt `DATABASE_URL` vor dem Import
von `main` um, damit die Produktivdatenbank unberührt bleibt.

## Dateien

```
main.py           API-Endpunkte und Datenbankverbindung
models.py         Datenmodell (Tabelle und Ein-/Ausgabeformate)
index.html        Weboberfläche, eigenständig ohne Build-Schritt
test_main.py      Testsuite
requirements.txt  Python-Abhängigkeiten
```

## Grenzen

Es gibt keine Benutzerverwaltung. Wer die Adresse kennt, sieht alle Einträge und kann
sie ändern. Für echte Finanzdaten wäre eine Anmeldung nötig, außerdem eine
Einschränkung der erlaubten Herkunft in der CORS-Konfiguration, die derzeit jede
Adresse zulässt.
