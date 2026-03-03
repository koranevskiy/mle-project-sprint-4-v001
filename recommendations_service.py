import logging
import os
from fastapi import FastAPI

from events_store import EventStore
from recs_store import RecommendationStore

logger = logging.getLogger("uvicorn.error")


def init_rec_store():
    rec_store = RecommendationStore()
    
    recs_dir_path = os.path.join(os.getcwd(), "recsys", "recommendations")
    personal_recs_path = os.path.join(recs_dir_path, "recommendations.parquet")
    online_recs_path = os.path.join(recs_dir_path, "similar.parquet")
    default_recs_path = os.path.join(recs_dir_path, "top_popular.parquet")
    
    rec_store.load("personal", personal_recs_path)
    rec_store.load("online", online_recs_path)
    rec_store.load("default", default_recs_path)
    
    return rec_store

def init_event_store():
    return EventStore()


def dedup_ids(ids):
    """
    Дедублицирует список идентификаторов, оставляя только первое вхождение
    """
    seen = set()
    ids = [id for id in ids if not (id in seen or seen.add(id))]

    return ids


rec_store = init_rec_store()
event_store = init_event_store()

app = FastAPI(title="recommendations")

@app.get("/offline_recs/stats")
async def offline_recs_stats():
    return rec_store.stats()

@app.post("/event")
async def put_event(user_id: int, item_id: int):
    """
    Сохраняет событие для user_id, item_id
    """

    event_store.put(user_id, item_id)

    return {"result": "ok"}

@app.get("/event")
async def get_events(user_id: int, k: int): 
    """
    Возвращает события для пользователя
    """
    try:
        user_events = event_store.get(user_id, k)
    except KeyError:
        user_events = []

    return user_events

@app.post("/recommendations_offline")
async def recommendations_offline(user_id: int, k: int = 100):
    """
    Возвращает список офлайн-рекомендаций длиной k для пользователя user_id
    """

    recs = rec_store.get_offline(user_id, k)

    return {"recs": recs}



@app.post("/recommendations_online")
async def recommendations_online(user_id: int, k: int = 100):
    """
    Возвращает список онлайн-рекомендаций длиной k для пользователя user_id
    """

    events = await get_events(user_id, k)

    items = []
    
    for item_id in events:
        # для каждого item_id получаем список похожих в item_similar_items
        item_similar_items = rec_store.get_online(item_id, k)
        items += item_similar_items
        

    # удаляем дубликаты, чтобы не выдавать одинаковые рекомендации
    recs = dedup_ids(items)[:k]

    return {"recs": recs}

@app.post("/recommendations")
async def recommendations(user_id: int, k: int = 100):
    """
    Возвращает список рекомендаций длиной k для пользователя user_id
    """

    recs_offline = await recommendations_offline(user_id, k)
    recs_online = await recommendations_online(user_id, k)

    recs_offline = recs_offline["recs"]
    recs_online = recs_online["recs"]

    recs_blended = []

    min_length = min(len(recs_offline), len(recs_online))
    # чередуем элементы из списков, пока позволяет минимальная длина
    for i in range(min_length):
        recs_blended.append(recs_online[i])
        recs_blended.append(recs_offline[i])

    # добавляем оставшиеся элементы в конец
    recs_blended = recs_blended + (recs_offline if len(recs_offline) >= len(recs_online) else recs_offline)[min_length:]

    # удаляем дубликаты
    recs_blended = dedup_ids(recs_blended)
    
        # оставляем только первые k рекомендаций
    recs_blended = recs_blended[:k]

    return {"recs": recs_blended}