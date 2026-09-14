"""Automatische Tests fuer das Finanz-Tracker-Backend.

Wichtig: Die Testdatenbank wird gesetzt, BEVOR main importiert wird.
Sonst wuerde main sich mit der echten Neon-Datenbank verbinden.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-geheimnis-nur-fuer-tests"

# bcrypt-Hash des Passworts "geheim123", nur fuer die Tests
import bcrypt as _bcrypt
os.environ["PASSWORT_HASH"] = _bcrypt.hashpw(b"geheim123", _bcrypt.gensalt()).decode()

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from main import app, engine


@pytest.fixture
def client():
    """Jeder Test startet mit einer komplett leeren Datenbank."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with TestClient(app) as c:
        # Einmal anmelden, Token fuer alle folgenden Anfragen hinterlegen
        token = c.post("/login", json={"passwort": "geheim123"}).json()["token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


@pytest.fixture
def anonym():
    """Client ohne Anmeldung, fuer die Zugriffstests."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


def lege_an(client, betrag, kategorie, datum, notiz=None):
    """Hilfsfunktion, damit die Tests selbst kurz bleiben."""
    return client.post("/expenses", json={
        "betrag": betrag, "kategorie": kategorie, "datum": datum, "notiz": notiz
    })


def test_ausgabe_anlegen(client):
    antwort = lege_an(client, 25.50, "Lebensmittel", "2026-09-02", "Wocheneinkauf")
    assert antwort.status_code == 200
    daten = antwort.json()
    assert daten["betrag"] == 25.50
    assert daten["kategorie"] == "Lebensmittel"
    assert daten["id"] > 0            # Datenbank hat eine ID vergeben


def test_leere_liste_am_anfang(client):
    assert client.get("/expenses").json() == []


def test_alle_ausgaben_abrufen(client):
    lege_an(client, 10.0, "Transport", "2026-09-01")
    lege_an(client, 20.0, "Lebensmittel", "2026-09-02")
    assert len(client.get("/expenses").json()) == 2


def test_nach_kategorie_filtern(client):
    lege_an(client, 10.0, "Transport", "2026-09-01")
    lege_an(client, 20.0, "Lebensmittel", "2026-09-02")

    treffer = client.get("/expenses?kategorie=Transport").json()
    assert len(treffer) == 1
    assert treffer[0]["kategorie"] == "Transport"


def test_filter_unterscheidet_gross_und_klein(client):
    lege_an(client, 10.0, "Transport", "2026-09-01")
    assert client.get("/expenses?kategorie=transport").json() == []


def test_loeschen(client):
    id_ = lege_an(client, 10.0, "Transport", "2026-09-01").json()["id"]

    assert client.delete(f"/expenses/{id_}").status_code == 200
    assert client.get("/expenses").json() == []


def test_loeschen_unbekannte_id_gibt_404(client):
    antwort = client.delete("/expenses/999")
    assert antwort.status_code == 404
    assert antwort.json()["detail"] == "Ausgabe nicht gefunden"


def test_betrag_muss_zahl_sein(client):
    antwort = lege_an(client, "keine Zahl", "Transport", "2026-09-01")
    assert antwort.status_code == 422      # FastAPI weist ungueltige Daten ab


def test_auswertung_gruppiert_und_summiert(client):
    lege_an(client, 25.50, "Lebensmittel", "2026-09-02")
    lege_an(client, 12.30, "Lebensmittel", "2026-09-10")
    lege_an(client, 15.00, "Transport", "2026-09-05")

    auswertung = client.get("/summary").json()
    assert len(auswertung) == 2
    assert auswertung[0] == {"kategorie": "Lebensmittel", "summe": 37.80, "anzahl": 2}
    assert auswertung[1]["summe"] == 15.00    # groesste Kategorie steht vorn


def test_auswertung_nur_ein_monat(client):
    lege_an(client, 25.50, "Lebensmittel", "2026-09-02")
    lege_an(client, 80.00, "Miete", "2026-08-01")

    september = client.get("/summary?monat=2026-09").json()
    assert len(september) == 1
    assert september[0]["kategorie"] == "Lebensmittel"


def test_auswertung_bezieht_monatsende_ein(client):
    lege_an(client, 5.0, "Test", "2026-02-28")    # letzter Tag im Februar 2026
    assert len(client.get("/summary?monat=2026-02").json()) == 1


def test_auswertung_leerer_monat(client):
    lege_an(client, 25.50, "Lebensmittel", "2026-09-02")
    assert client.get("/summary?monat=2026-07").json() == []


def test_auswertung_ungueltiger_monat(client):
    assert client.get("/summary?monat=quatsch").status_code == 400


# --- Tests fuer das Bearbeiten ---

def test_aendern(client):
    id_ = lege_an(client, 10.0, "Transport", "2026-09-01", "Bahn").json()["id"]

    antwort = client.put(f"/expenses/{id_}", json={
        "betrag": 12.50, "kategorie": "Transport", "datum": "2026-09-03", "notiz": "Bahn, teurer"
    })
    assert antwort.status_code == 200
    assert antwort.json()["betrag"] == 12.50
    assert antwort.json()["id"] == id_          # ID bleibt dieselbe


def test_aendern_wirkt_dauerhaft(client):
    id_ = lege_an(client, 10.0, "Transport", "2026-09-01").json()["id"]
    client.put(f"/expenses/{id_}", json={
        "betrag": 99.0, "kategorie": "Miete", "datum": "2026-09-01", "notiz": None
    })

    eintraege = client.get("/expenses").json()
    assert len(eintraege) == 1                   # kein zweiter Eintrag entstanden
    assert eintraege[0]["kategorie"] == "Miete"
    assert eintraege[0]["betrag"] == 99.0


def test_aendern_verschiebt_die_auswertung(client):
    id_ = lege_an(client, 20.0, "Transport", "2026-09-01").json()["id"]
    client.put(f"/expenses/{id_}", json={
        "betrag": 20.0, "kategorie": "Lebensmittel", "datum": "2026-09-01", "notiz": None
    })

    auswertung = client.get("/summary?monat=2026-09").json()
    assert auswertung == [{"kategorie": "Lebensmittel", "summe": 20.0, "anzahl": 1}]


def test_aendern_unbekannte_id_gibt_404(client):
    antwort = client.put("/expenses/999", json={
        "betrag": 1.0, "kategorie": "Test", "datum": "2026-09-01", "notiz": None
    })
    assert antwort.status_code == 404


# --- Tests fuer die Anmeldung ---

def test_ohne_token_kein_zugriff(anonym):
    assert anonym.get("/expenses").status_code == 401
    assert anonym.post("/expenses", json={
        "betrag": 1.0, "kategorie": "Test", "datum": "2026-09-01", "notiz": None
    }).status_code == 401
    assert anonym.delete("/expenses/1").status_code == 401
    assert anonym.get("/summary").status_code == 401


def test_falsches_passwort(anonym):
    antwort = anonym.post("/login", json={"passwort": "falsch"})
    assert antwort.status_code == 401
    assert "token" not in antwort.json()


def test_richtiges_passwort_gibt_token(anonym):
    antwort = anonym.post("/login", json={"passwort": "geheim123"})
    assert antwort.status_code == 200
    assert len(antwort.json()["token"]) > 20


def test_gefaelschter_token_wird_abgelehnt(anonym):
    anonym.headers["Authorization"] = "Bearer ich.bin.kein.token"
    assert anonym.get("/expenses").status_code == 401


def test_token_mit_falschem_geheimnis_wird_abgelehnt(anonym):
    import jwt
    from datetime import datetime, timedelta, timezone
    fremder = jwt.encode(
        {"sub": "besitzer", "exp": datetime.now(timezone.utc) + timedelta(days=1)},
        "anderes-geheimnis", algorithm="HS256")
    anonym.headers["Authorization"] = f"Bearer {fremder}"
    assert anonym.get("/expenses").status_code == 401


def test_abgelaufener_token_wird_abgelehnt(anonym):
    import jwt
    from datetime import datetime, timedelta, timezone
    alt = jwt.encode(
        {"sub": "besitzer", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        os.environ["SECRET_KEY"], algorithm="HS256")
    anonym.headers["Authorization"] = f"Bearer {alt}"
    antwort = anonym.get("/expenses")
    assert antwort.status_code == 401
    assert antwort.json()["detail"] == "Anmeldung abgelaufen"


def test_startseite_bleibt_offen(anonym):
    assert anonym.get("/").status_code == 200
