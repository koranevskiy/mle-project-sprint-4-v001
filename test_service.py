import requests
import json
import time
from datetime import datetime

class RecommendationServiceTester:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.test_results = []
        
    def log_test(self, test_name: str, test_data: dict, response_data: dict, success: bool):
        """Логирование результатов теста"""
        self.test_results.append({
            "test_name": test_name,
            "timestamp": datetime.now().isoformat(),
            "test_data": test_data,
            "response": response_data,
            "success": success
        })
        
        # Вывод в консоль
        print(f"\n{'='*60}")
        print(f"ТЕСТ: {test_name}")
        print(f"{'='*60}")
        print(f"Входные данные: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
        print(f"Ответ: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        print(f"Статус: {'✅ УСПЕШНО' if success else '❌ ОШИБКА'}")
    
    def test_health(self):
        """Проверка доступности сервиса"""
        try:
            response = requests.get(f"{self.base_url}/offline_recs/stats")
            success = response.status_code == 200
            self.log_test(
                "Health Check",
                {"endpoint": "/offline_recs/stats"},
                response.json() if success else {"error": f"HTTP {response.status_code}"},
                success
            )
            return success
        except Exception as e:
            self.log_test(
                "Health Check",
                {"endpoint": "/offline_recs/stats"},
                {"error": str(e)},
                False
            )
            return False
    
    def create_user_history(self, user_id: int, items: list):
        """
        Создание истории для пользователя через POST /event
        """
        history_results = []
        
        for item_id in items:
            try:
                # Отправляем POST запрос на /event с параметрами user_id и item_id
                response = requests.post(
                    f"{self.base_url}/event",
                    params={"user_id": user_id, "item_id": item_id}
                )
                
                history_results.append({
                    "user_id": user_id,
                    "item_id": item_id,
                    "response": response.json(),
                    "status_code": response.status_code,
                    "success": response.status_code == 200
                })
                
                # Небольшая задержка между запросами
                time.sleep(0.1)
                
            except Exception as e:
                history_results.append({
                    "user_id": user_id,
                    "item_id": item_id,
                    "error": str(e),
                    "success": False
                })
        
        return history_results
    
    def get_user_events(self, user_id: int, k: int = 10):
        """
        Получение событий пользователя через GET /event
        """
        try:
            response = requests.get(
                f"{self.base_url}/event",
                params={"user_id": user_id, "k": k}
            )
            
            return {
                "events": response.json() if response.status_code == 200 else [],
                "status_code": response.status_code,
                "success": response.status_code == 200
            }
        except Exception as e:
            return {
                "events": [],
                "error": str(e),
                "success": False
            }
    
    def test_cold_start_user(self):
        """
        Тест 1: Пользователь без персональных рекомендаций
        Используем пользователя с ID, которого нет в персональных рекомендациях
        """
        test_data = {
            "user_id": 999999,
            "k": 10
        }
        
        try:
            # Получаем офлайн-рекомендации (должны вернуться популярные)
            response = requests.post(
                f"{self.base_url}/recommendations_offline",
                params=test_data
            )
            
            response_data = response.json()
            success = response.status_code == 200
            
            # Проверяем, что рекомендации есть (должны быть популярные)
            if success:
                recs = response_data.get("recs", [])
                success = len(recs) == test_data["k"]
                response_data["recs_count"] = len(recs)
            
            self.log_test(
                "Пользователь без персональных рекомендаций (холодный старт)",
                test_data,
                response_data,
                success
            )
            
            return success
        except Exception as e:
            self.log_test(
                "Пользователь без персональных рекомендаций",
                test_data,
                {"error": str(e)},
                False
            )
            return False
    
    def test_user_without_history(self):
        """
        Тест 2: Пользователь с персональными рекомендациями, но без онлайн-истории
        """
        user_id = 1374582  # Предполагаем, что этот пользователь есть в персональных рекомендациях
        test_data = {
            "user_id": user_id,
            "k": 15
        }
        
        try:
            # Сначала проверяем, что у пользователя действительно нет истории
            events_before = self.get_user_events(user_id, k=5)
            
            # Проверяем офлайн-рекомендации (должны быть персональные)
            offline_response = requests.post(
                f"{self.base_url}/recommendations_offline",
                params=test_data
            )
            
            # Проверяем онлайн-рекомендации (должны быть пустыми, так как нет истории)
            online_response = requests.post(
                f"{self.base_url}/recommendations_online",
                params=test_data
            )
            
            # Проверяем смешанные рекомендации
            blended_response = requests.post(
                f"{self.base_url}/recommendations",
                params=test_data
            )
            
            response_data = {
                "events_before": events_before,
                "offline_recs": offline_response.json() if offline_response.status_code == 200 else {"error": f"HTTP {offline_response.status_code}"},
                "online_recs": online_response.json() if online_response.status_code == 200 else {"error": f"HTTP {online_response.status_code}"},
                "blended_recs": blended_response.json() if blended_response.status_code == 200 else {"error": f"HTTP {blended_response.status_code}"}
            }
            
            # Проверяем успешность
            offline_success = offline_response.status_code == 200
            online_success = online_response.status_code == 200
            blended_success = blended_response.status_code == 200
            
            if offline_success:
                response_data["offline_recs"]["count"] = len(response_data["offline_recs"].get("recs", []))
            if online_success:
                response_data["online_recs"]["count"] = len(response_data["online_recs"].get("recs", []))
            if blended_success:
                response_data["blended_recs"]["count"] = len(response_data["blended_recs"].get("recs", []))
            
            success = offline_success and online_success and blended_success
            
            self.log_test(
                "Пользователь с персональными рекомендациями, без онлайн-истории",
                test_data,
                response_data,
                success
            )
            
            return success
        except Exception as e:
            self.log_test(
                "Пользователь с персональными рекомендациями, без онлайн-истории",
                test_data,
                {"error": str(e)},
                False
            )
            return False
    
    def test_user_with_history(self):
        """
        Тест 3: Пользователь с персональными рекомендациями и онлайн-историей
        """
        user_id = 4  
        history_items = [94642241]
        test_data = {
            "user_id": user_id,
            "k": 20,
            "history_items": history_items
        }
        
        try:
            # ШАГ 1: Создаем историю через POST /event
            print(f"\n   📝 Создаем историю для пользователя {user_id}...")
            history_creation = self.create_user_history(user_id, history_items)
            
            # Проверяем, что все события успешно созданы
            history_success = all(item.get("success", False) for item in history_creation)
            
            # ШАГ 2: Получаем события пользователя через GET /event
            print(f"   🔍 Получаем события пользователя {user_id}...")
            user_events = self.get_user_events(user_id, k=10)
            
            # ШАГ 3: Получаем офлайн-рекомендации
            print(f"   💾 Получаем офлайн-рекомендации...")
            offline_response = requests.post(
                f"{self.base_url}/recommendations_offline",
                params={"user_id": user_id, "k": test_data["k"]}
            )
            
            # ШАГ 4: Получаем онлайн-рекомендации (должны учитывать историю)
            print(f"   🌐 Получаем онлайн-рекомендации...")
            online_response = requests.post(
                f"{self.base_url}/recommendations_online",
                params={"user_id": user_id, "k": test_data["k"]}
            )
            
            # ШАГ 5: Получаем смешанные рекомендации
            print(f"   🔀 Получаем смешанные рекомендации...")
            blended_response = requests.post(
                f"{self.base_url}/recommendations",
                params={"user_id": user_id, "k": test_data["k"]}
            )
            
            response_data = {
                "history_creation": history_creation,
                "history_success": history_success,
                "user_events": user_events,
                "offline_recs": offline_response.json() if offline_response.status_code == 200 else {"error": f"HTTP {offline_response.status_code}"},
                "online_recs": online_response.json() if online_response.status_code == 200 else {"error": f"HTTP {online_response.status_code}"},
                "blended_recs": blended_response.json() if blended_response.status_code == 200 else {"error": f"HTTP {blended_response.status_code}"}
            }
            
            # Добавляем counts для удобства
            if offline_response.status_code == 200:
                response_data["offline_recs"]["count"] = len(response_data["offline_recs"].get("recs", []))
            if online_response.status_code == 200:
                response_data["online_recs"]["count"] = len(response_data["online_recs"].get("recs", []))
            if blended_response.status_code == 200:
                response_data["blended_recs"]["count"] = len(response_data["blended_recs"].get("recs", []))
            
            # Проверяем успешность
            success = all([
                history_success,
                user_events["success"],
                offline_response.status_code == 200,
                online_response.status_code == 200,
                blended_response.status_code == 200,
                len(user_events.get("events", [])) > 0,  # Должны быть события
                len(online_response.json().get("recs", [])) > 0  # Онлайн-рекомендации не должны быть пустыми
            ])
            
            self.log_test(
                "Пользователь с персональными рекомендациями и онлайн-историей",
                test_data,
                response_data,
                success
            )
            
            return success
        except Exception as e:
            self.log_test(
                "Пользователь с персональными рекомендациями и онлайн-историей",
                test_data,
                {"error": str(e)},
                False
            )
            return False
    
    def test_strategy_blending(self):
        """
        Дополнительный тест: Проверка стратегии смешивания рекомендаций
        Проверяем, что в смешанных рекомендациях есть элементы как из офлайн, так и из онлайн
        """
        user_id = 54321
        history_items = [99262]  # Создаем историю
        test_data = {
            "user_id": user_id,
            "k": 10
        }
        
        try:
            # Создаем историю
            print(f"\n   📝 Создаем историю для проверки смешивания...")
            self.create_user_history(user_id, history_items)
            
            # Получаем отдельные компоненты
            offline_response = requests.post(
                f"{self.base_url}/recommendations_offline",
                params=test_data
            )
            online_response = requests.post(
                f"{self.base_url}/recommendations_online",
                params=test_data
            )
            blended_response = requests.post(
                f"{self.base_url}/recommendations",
                params=test_data
            )
            
            if any(r.status_code != 200 for r in [offline_response, online_response, blended_response]):
                raise Exception("One of the endpoints returned non-200 status")
            
            offline_recs = offline_response.json().get("recs", [])
            online_recs = online_response.json().get("recs", [])
            blended_recs = blended_response.json().get("recs", [])
            
            # Анализируем стратегию смешивания
            # Проверяем чередование (первые элементы должны чередоваться)
            blending_pattern = []
            for i in range(min(5, len(blended_recs))):
                if i < len(online_recs) and blended_recs[i] in online_recs:
                    blending_pattern.append("online")
                elif i < len(offline_recs) and blended_recs[i] in offline_recs:
                    blending_pattern.append("offline")
                else:
                    blending_pattern.append("unknown")
            
            strategy_analysis = {
                "blended_count": len(blended_recs),
                "offline_count": len(offline_recs),
                "online_count": len(online_recs),
                "contains_offline": any(r in offline_recs for r in blended_recs[:5]),
                "contains_online": any(r in online_recs for r in blended_recs[:5]),
                "blending_pattern": blending_pattern,
                "unique_in_blended": len(set(blended_recs)) == len(blended_recs)  # Проверка на дубликаты
            }
            
            response_data = {
                "strategy_analysis": strategy_analysis,
                "offline_recs": offline_recs[:5],
                "online_recs": online_recs[:5],
                "blended_recs": blended_recs
            }
            
            # Успешно, если в смешанных есть элементы из обоих источников
            success = strategy_analysis["contains_offline"] and strategy_analysis["contains_online"]
            
            self.log_test(
                "Проверка стратегии смешивания рекомендаций",
                {**test_data, "history_items": history_items},
                response_data,
                success
            )
            
            return success
        except Exception as e:
            self.log_test(
                "Проверка стратегии смешивания рекомендаций",
                {**test_data, "history_items": history_items},
                {"error": str(e)},
                False
            )
            return False
    
    def run_all_tests(self):
        """Запуск всех тестов"""
        print("\n" + "="*70)
        print("ЗАПУСК ТЕСТИРОВАНИЯ МИКРОСЕРВИСА РЕКОМЕНДАЦИЙ")
        print("="*70)
        print(f"Время начала: {datetime.now().isoformat()}")
        print("="*70)
        
        # Проверяем доступность сервиса
        if not self.test_health():
            print("\n❌ СЕРВИС НЕДОСТУПЕН!")
            print("Убедитесь, что микросервис запущен на http://localhost:8000")
            return
        
        print("\n✅ Сервис доступен, начинаем тестирование...")
        time.sleep(1)
        
        # Тестовые сценарии
        tests = [
            ("Тест 1: Холодный старт (нет персональных)", self.test_cold_start_user),
            ("Тест 2: Есть персональные, нет истории", self.test_user_without_history),
            ("Тест 3: Есть персональные и история", self.test_user_with_history),
            ("Тест 4: Проверка стратегии смешивания", self.test_strategy_blending)
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n▶️ Запуск: {test_name}")
            try:
                success = test_func()
                results.append((test_name, success))
                time.sleep(1)  # Пауза между тестами
            except Exception as e:
                print(f"  ❌ Ошибка выполнения: {e}")
                results.append((test_name, False))
        
        # Итоги
        print("\n" + "="*70)
        print("ИТОГИ ТЕСТИРОВАНИЯ")
        print("="*70)
        
        all_passed = True
        for test_name, success in results:
            status = "✅ ПРОЙДЕН" if success else "❌ ПРОВАЛЕН"
            print(f"{status} - {test_name}")
            if not success:
                all_passed = False
        
        print("="*70)
        print(f"ОБЩИЙ РЕЗУЛЬТАТ: {'✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ' if all_passed else '❌ ЕСТЬ ПРОБЛЕМЫ'}")
        print("="*70)
        
        # Сохраняем результаты в файл
        self.save_results()
        
        return all_passed
    
    def save_results(self, filename="test_service.log"):
        """Сохранение результатов тестирования в файл"""
        output = {
            "test_session": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": len(self.test_results),
                "successful_tests": sum(1 for r in self.test_results if r["success"]),
                "failed_tests": sum(1 for r in self.test_results if not r["success"])
            },
            "results": self.test_results
        }
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Результаты сохранены в файл: {filename}")

if __name__ == "__main__":
    # Создаем тестер
    tester = RecommendationServiceTester()
    
    # Запускаем тесты
    tester.run_all_tests()