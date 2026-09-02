from fastapi import FastAPI # type: ignore
from sqlmodel import SQLModel, Session, create_engine, select # type: ignore
from models import Expense, ExpenseCreate, ExpenseRead

DATABASE_URL = "sqlite:///./finanzen.db"
engine = create_engine(DATABASE_URL)

app = FastAPI()

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
def get_expenses():
    with Session(engine) as session:
        expenses = session.exec(select(Expense)).all()
        return expenses