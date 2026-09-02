from sqlmodel import SQLModel, Field # type: ignore
from datetime import date
from typing import Optional

class ExpenseBase(SQLModel):
    betrag: float
    kategorie: str
    datum: date
    notiz: Optional[str] = None

class Expense(ExpenseBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseRead(ExpenseBase):
    id: int