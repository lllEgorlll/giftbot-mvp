from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

app = FastAPI(title="GiftBot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = "sqlite:///./giftbot.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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

@app.post("/gift-requests")
def create_request(request: dict, db: Session = Depends(get_db)):
    db_request = GiftRequest(**request)
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return {"id": db_request.id, "message": "Запрос сохранён"}

@app.get("/gift-requests")
def get_requests(db: Session = Depends(get_db)):
    requests = db.query(GiftRequest).order_by(GiftRequest.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "created_at": r.created_at.isoformat(),
            "gender": r.gender,
            "age": r.age,
            "occasion": r.occasion,
            "budget": r.budget,
            "closeness": r.closeness,
            "interests": r.interests,
            "selected_gift": r.selected_gift
        }
        for r in requests
    ]

# ← НОВОЕ: УДАЛЕНИЕ ОДНОЙ ЗАПИСИ
@app.delete("/gift-requests/{request_id}")
def delete_request(request_id: int, db: Session = Depends(get_db)):
    request = db.query(GiftRequest).filter(GiftRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    db.delete(request)
    db.commit()
    return {"message": f"Запись {request_id} успешно удалена"}

# ← НОВОЕ: ОЧИСТИТЬ ВСЮ ТАБЛИЦУ (если хочешь удалить всё сразу)
@app.delete("/gift-requests")
def delete_all_requests(db: Session = Depends(get_db)):
    db.query(GiftRequest).delete()
    db.commit()
    return {"message": "Все записи удалены"}

@app.get("/")
def root():
    return {"message": "GiftBot API работает! 🚀"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)