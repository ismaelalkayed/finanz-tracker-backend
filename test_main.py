"""
Tests fuer den Finanz-Tracker Backend.

Nutzt eine eigene Test-Datenbank (nicht finanzen.db!), damit die Tests
deine echten Daten nie anfassen. Ausfuehren mit: pytest
"""

import os
from fastapi.testclient import TestClient # type: ignore
from sqlmodel import SQLModel, create_engine # type: ignore
import main

# main.py auf eine separate Test-Datenbank umbiegen, statt der echten
TEST_DB_FILE = "test_finanzen.db"
test_engine = create_engine(f"sqlite:///{TEST_DB_FILE}")
main.engine = test_engine

client = TestClient(main.app)


def setup_function():
    """Laeuft vor JEDEM einzelnen Test: sorgt fuer eine leere, frische Datenbank."""
    SQLModel.metadata.drop_all(test_engine)
    SQLModel.metadata.create_all(test_engine)


def teardown_module(module):
    """Laeuft einmal, nachdem ALLE Tests durchgelaufen sind: raeumt die Testdatei weg."""
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)


def test_create_expense():
    response = client.post("/expenses", json={
        "betrag": 25.50,
        "kategorie": "Lebensmittel",
        "datum": "2026-09-02",
        "notiz": "Wocheneinkauf"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["betrag"] == 25.50
    assert data["kategorie"] == "Lebensmittel"
    assert "id" in data


def test_get_expenses_empty():
    response = client.get("/expenses")
    assert response.status_code == 200
    assert response.json() == []


def test_get_expenses_after_creating():
    client.post("/expenses", json={"betrag": 10, "kategorie": "Transport", "datum": "2026-09-02"})
    response = client.get("/expenses")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_filter_by_kategorie():
    client.post("/expenses", json={"betrag": 25.50, "kategorie": "Lebensmittel", "datum": "2026-09-02"})
    client.post("/expenses", json={"betrag": 15.00, "kategorie": "Transport", "datum": "2026-09-02"})

    response = client.get("/expenses?kategorie=Lebensmittel")
    assert response.status_code == 200
    ergebnisse = response.json()
    assert len(ergebnisse) == 1
    assert ergebnisse[0]["kategorie"] == "Lebensmittel"


def test_delete_expense():
    erstellt = client.post("/expenses", json={"betrag": 5, "kategorie": "Sonstiges", "datum": "2026-09-02"})
    expense_id = erstellt.json()["id"]

    geloescht = client.delete(f"/expenses/{expense_id}")
    assert geloescht.status_code == 200

    verbleibend = client.get("/expenses")
    assert len(verbleibend.json()) == 0


def test_delete_nonexistent_expense_returns_404():
    response = client.delete("/expenses/9999")
    assert response.status_code == 404