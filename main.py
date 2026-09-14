import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from sqlalchemy import func
from datetime import date
from calendar import monthrange
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session, create_engine, select
from typing import Optional
from models import Expense, ExpenseCreate, ExpenseRead

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./finanzen.db")
PASSWORT_HASH = os.getenv("PASSWORT_HASH", "")
SECRET_KEY = os.getenv("SECRET_KEY", "")
TOKEN_GUELTIG_TAGE = 7

engine = create_engine(DATABASE_URL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

sicherheit = HTTPBearer(auto_error=False)


class Anmeldung(SQLModel):
    passwort: str


def pruefe_token(zugang: HTTPAuthorizationCredentials = Depends(sicherheit)):
    if zugang is None:
        raise HTTPException(status_code=401, detail="Nicht angemeldet")
    try:
        jwt.decode(zugang.credentials, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Anmeldung abgelaufen")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token ungueltig")


@app.post("/login")
def login(daten: Anmeldung):
    if not PASSWORT_HASH or not SECRET_KEY:
        raise HTTPException(status_code=500, detail="Server ist nicht fuer Anmeldung eingerichtet")

    if not bcrypt.checkpw(daten.passwort.encode(), PASSWORT_HASH.encode()):
        raise HTTPException(status_code=401, detail="Passwort falsch")

    ablauf = datetime.now(timezone.utc) + timedelta(days=TOKEN_GUELTIG_TAGE)
    token = jwt.encode({"sub": "besitzer", "exp": ablauf}, SECRET_KEY, algorithm="HS256")
    return {"token": token, "gueltig_bis": ablauf.isoformat()}


@app.get("/")
def read_root():
    return {"message": "Finanz-Tracker Backend läuft!"}

@app.post("/expenses", response_model=ExpenseRead, dependencies=[Depends(pruefe_token)])
def create_expense(expense: ExpenseCreate):
    with Session(engine) as session:
        db_expense = Expense.model_validate(expense)
        session.add(db_expense)
        session.commit()
        session.refresh(db_expense)
        return db_expense

@app.get("/expenses", response_model=list[ExpenseRead], dependencies=[Depends(pruefe_token)])
def get_expenses(kategorie: Optional[str] = None):
    with Session(engine) as session:
        abfrage = select(Expense)
        if kategorie:
            abfrage = abfrage.where(Expense.kategorie == kategorie)
        return session.exec(abfrage).all()

@app.put("/expenses/{expense_id}", response_model=ExpenseRead, dependencies=[Depends(pruefe_token)])
def update_expense(expense_id: int, expense: ExpenseCreate):
    with Session(engine) as session:
        db_expense = session.get(Expense, expense_id)
        if not db_expense:
            raise HTTPException(status_code=404, detail="Ausgabe nicht gefunden")
        for key, value in expense.model_dump().items():
            setattr(db_expense, key, value)
        session.add(db_expense)
        session.commit()
        session.refresh(db_expense)
        return db_expense


@app.delete("/expenses/{expense_id}", dependencies=[Depends(pruefe_token)])
def delete_expense(expense_id: int):
    with Session(engine) as session:
        expense = session.get(Expense, expense_id)
        if not expense:
            raise HTTPException(status_code=404, detail="Ausgabe nicht gefunden")
        session.delete(expense)
        session.commit()
        return {"ok": True, "geloescht": expense_id}
    
@app.get("/summary", dependencies=[Depends(pruefe_token)])
def get_summary(monat: Optional[str] = None):
    with Session(engine) as session:
        abfrage = (
            select(Expense.kategorie,
                   func.sum(Expense.betrag).label("summe"),
                   func.count(Expense.id).label("anzahl"))
            .group_by(Expense.kategorie)
            .order_by(func.sum(Expense.betrag).desc())
        )
        if monat:
            try:
                jahr, nummer = int(monat[:4]), int(monat[5:7])
                erster = date(jahr, nummer, 1)
                letzter = date(jahr, nummer, monthrange(jahr, nummer)[1])
            except (ValueError, IndexError):
                raise HTTPException(status_code=400, detail="Monat bitte als JJJJ-MM angeben")
            abfrage = abfrage.where(Expense.datum >= erster, Expense.datum <= letzter)

        zeilen = session.exec(abfrage).all()
        return [
            {"kategorie": k, "summe": round(float(s), 2), "anzahl": a}
            for k, s, a in zeilen
        ]