from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import uvicorn

app = FastAPI(title="GiftBot API")

# ==================== CORS (важно для GitHub Pages) ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                    # для MVP можно *, потом заменишь на свой github.io
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== SQLite ====================
DATABASE_URL = "sqlite:///./giftbot.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Стало
from sqlalchemy.orm import declarative_base   # ← добавь этот импорт в начало файла

Base = declarative_base()

# Сущность из ПР-3 (GiftRequest)
class GiftRequest(Base):
    __tablename__ = "gift_requests"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    gender = Column(String)
    age = Column(Integer)
    occasion = Column(String)
    budget = Column(Integer)
    closeness = Column(String)
    interests = Column(Text)
    selected_gift = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic модели
class GiftRequestCreate(BaseModel):
    gender: str
    age: int
    occasion: str
    budget: int
    closeness: str
    interests: str = ""

class GiftRequestResponse(BaseModel):
    id: int
    created_at: datetime
    gender: str
    age: int
    occasion: str
    budget: int
    closeness: str
    interests: str
    selected_gift: str | None

# ==================== API ====================
@app.post("/gift-requests", response_model=GiftRequestResponse)
def create_request(request: GiftRequestCreate, db: Session = Depends(get_db)):
    db_request = GiftRequest(**request.model_dump())
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request

@app.get("/gift-requests", response_model=list[GiftRequestResponse])
def get_requests(db: Session = Depends(get_db)):
    return db.query(GiftRequest).order_by(GiftRequest.created_at.desc()).all()

# Для теста
@app.get("/")
def root():
    return {"message": "GiftBot API работает! 🚀"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)