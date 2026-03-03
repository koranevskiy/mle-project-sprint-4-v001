import logging
import pandas as pd

logger = logging.getLogger("uvicorn.error")

class RecommendationStore:

    def __init__(self):
        self._recs = {"personal": None, "default": None, "online": None}
        self._stats = {
            "request_personal_count": 0,
            "request_default_count": 0,
            "request_online_count": 0,
        }

    def load(self, type, path, **kwargs):
        """
        Загружает рекомендации из файла
        """
        logger.info(f"Loading recommendations, type: {type}")
        self._recs[type] = pd.read_parquet(path, **kwargs)
        if type == "default":
            self._recs[type] = self._recs[type].rename(columns={"track_id": "item_id"})
        if type == "personal":
            self._recs[type] = self._recs[type].set_index("user_id")
        if type == "online":
            self._recs[type] = self._recs[type].set_index("item_id_1")
            
        logger.info(f"Loaded {type} recommendations")
        print(self._recs)

    
    def get_offline(self, user_id: int, k: int=100):
        """
        Возвращает список рекомендаций для пользователя
        """
        try:
            recs = self._recs["personal"].loc[user_id]
            recs = recs["item_id"].to_list()[:k]
            self._stats["request_personal_count"] += 1
        except KeyError:
            recs = self._recs["default"]
            recs = recs["item_id"].to_list()[:k]
            self._stats["request_default_count"] += 1
        except:
            logger.error(f"No recommendations found for user_id {user_id}")
            recs = []

        return recs
    
    def get_online(self, item_id: int, k: int = 100):
        try:
            recs = self._recs["online"].loc[item_id]
            if len(recs) == 0:
                logger.error(f"No online recommendation for item_id {item_id}")
                return []
            recs = recs["item_id_2"].to_list()[:k]
            self._stats["request_online_count"] += 1
            return recs
        except KeyError:
            return []

    def stats(self):
        logger.info("Stats for recommendations")
        for name, value in self._stats.items():
            logger.info(f"{name:<30} {value} ")
        return self._stats