from fastapi.middleware.cors import CORSMiddleware # type: ignore
from fastapi import FastAPI, HTTPException # type: ignore
from sqlmodel import SQLModel, Session, create_engine, select # type: ignore
from typing import Optional
from models import Expense, ExpenseCreate, ExpenseRead

DATABASE_URL = "sqlite:///./finanzen.db"
engine = create_engine(DATABASE_URL)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

@app.get("/")
def read_root():
    return {"message": "Finanz-Tracker Backend läuft!"}

@app.post("/expenses", response_model=ExpenseRead)
def create_expense(expense: ExpenseCreate):
    with Session(engine) as session:
        db_expense = Expense.model_validate(expense)
        session.add(db_expense)
        session.commit()
        session.refresh(db_expense)
        return db_expense

@app.get("/expenses", response_model=list[ExpenseRead])
def get_expenses(kategorie: Optional[str] = None):
    with Session(engine) as session:
        query = select(Expense)
        if kategorie:
            query = query.where(Expense.kategorie == kategorie)
        expenses = session.exec(query).all()
        return expenses

@app.delete("/expenses/{expense_id}")
@app.put("/expenses/{expense_id}", response_model=ExpenseRead)
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

def delete_expense(expense_id: int):
    with Session(engine) as session:
        expense = session.get(Expense, expense_id)
        if not expense:
            raise HTTPException(status_code=404, detail="Ausgabe nicht gefunden")
        session.delete(expense)
        session.commit()
        return {"message": f"Ausgabe {expense_id} gelöscht"}