from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import requests  # ← ДОБАВЛЕНО для HTTP-запросов к Битрикс24
import os

app = FastAPI(title="GiftBot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ↓↓↓ ЗАМЕНИТЕ НА ВАШ ВЕБХУК (уже есть) ↓↓↓
BITRIX24_WEBHOOK = "https://b24-756tbi.bitrix24.ru/rest/1/1rkznb6559d2y6si/"


# -----------------------------------------------
# Функция отправки данных в Битрикс24 (лиды)
# -----------------------------------------------
def send_to_bitrix24(lead_data: dict):
    print("\n=== ОТПРАВКА В BITRIX24 ===")
    print("Полученные данные из формы:", lead_data)

    url = f"{BITRIX24_WEBHOOK}crm.lead.add"

    # Пол: поддерживаем и английские, и русские варианты
    gender_raw = lead_data.get("gender", "")
    if gender_raw in ("female", "Женский"):
        gender_bitrix = "Женский"
    elif gender_raw in ("male", "Мужской"):
        gender_bitrix = "Мужской"
    else:
        gender_bitrix = gender_raw  # на всякий случай оставить как есть
    print("1. Пол (исходный → битрикс):", gender_raw, "→", gender_bitrix)

    # Повод: маппинг с учётом русских сокращений
    occasion_raw = lead_data.get("occasion", "")
    occasion_map = {
        "birthday": "День рождения",
        "new_year": "Новый год",
        "march_8": "8 Марта",
        "anniversary": "Годовщина",
        "ДР": "День рождения",
        "др": "День рождения",
        "НГ": "Новый год",
        "нг": "Новый год"
    }
    occasion_bitrix = occasion_map.get(occasion_raw, occasion_raw)
    print("2. Повод (исходный → битрикс):", occasion_raw, "→", occasion_bitrix)

    # Степень близости
    closeness_raw = lead_data.get("closeness", "")
    closeness_map = {
        "close": "Близкий",
        "acquaintance": "Знакомый",
        "colleague": "Коллега",
        "Родственник": "Близкий",
        "родственник": "Близкий"
    }
    closeness_bitrix = closeness_map.get(closeness_raw, closeness_raw)
    print("3. Близость (исходный → битрикс):", closeness_raw, "→", closeness_bitrix)

    # Возраст и бюджет – без изменений
    age_val = lead_data.get("age")
    try:
        age_int = int(age_val) if age_val is not None else 0
    except (ValueError, TypeError):
        age_int = 0
    print("4. Возраст →", age_int)

    budget_val = lead_data.get("budget")
    try:
        budget_int = int(budget_val) if budget_val is not None else 0
    except (ValueError, TypeError):
        budget_int = 0
    print("5. Бюджет →", budget_int)

    interests_val = lead_data.get("interests", "")
    print("6. Интересы:", interests_val)

    # Формируем поля лида – коды полей оставляем как есть (они правильные)
    fields = {
        "TITLE": f"GiftBot: {gender_bitrix}, {age_int} лет",
        "NAME": f"Запрос от {gender_bitrix} {age_int}",
        "COMMENTS": f"Повод: {occasion_bitrix}\nИнтересы: {interests_val}",

        "UfCrm1778219345": gender_bitrix,
        "UfCrm1778219365": age_int,
        "UfCrm1778219376": occasion_bitrix,
        "UfCrm1778219390": budget_int,
        "UfCrm1778219418": closeness_bitrix,
        "UfCrm1778219437": interests_val
    }

    print("\n--- Что отправляем в Bitrix24 ---")
    for k, v in fields.items():
        print(f"  {k}: {v!r}")

    payload = {"fields": fields}

    try:
        response = requests.post(url, json=payload, timeout=10)
        print("\n--- Ответ Bitrix24 ---")
        print(f"Статус: {response.status_code}")
        print(f"Тело: {response.text}")
        response.raise_for_status()
        result = response.json()
        if result.get("result"):
            print(f"✅ Лид создан, ID: {result['result']}")
        else:
            print(f"❌ Ошибка: {result}")
    except Exception as e:
        print(f"❌ Исключение: {e}")
    print("=== КОНЕЦ ОТЛАДКИ ===\n")

# -----------------------------------------------
# База данных SQLite (как было)
# -----------------------------------------------
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


# -----------------------------------------------
# Эндпоинты API
# -----------------------------------------------
@app.post("/gift-requests")
def create_request(request: dict, db: Session = Depends(get_db)):
    # Сохраняем в локальную БД
    db_request = GiftRequest(**request)
    db.add(db_request)
    db.commit()
    db.refresh(db_request)

    # Отправляем в Битрикс24 (неблокирующе, но можно синхронно)
    send_to_bitrix24(request)

    return {"id": db_request.id, "message": "Запрос сохранён и отправлен в Битрикс24"}


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


@app.delete("/gift-requests/{request_id}")
def delete_request(request_id: int, db: Session = Depends(get_db)):
    request = db.query(GiftRequest).filter(GiftRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    db.delete(request)
    db.commit()
    return {"message": f"Запись {request_id} успешно удалена"}


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