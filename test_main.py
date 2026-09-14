"""Automatische Tests fuer das Finanz-Tracker-Backend.

Wichtig: Die Testdatenbank wird gesetzt, BEVOR main importiert wird.
Sonst wuerde main sich mit der echten Neon-Datenbank verbinden.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

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
