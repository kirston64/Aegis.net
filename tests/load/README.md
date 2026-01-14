# 🔥 Aegis.net Load Testing Suite

Легальный инструмент нагрузочного тестирования для проверки устойчивости Aegis.net.

## Быстрый старт

```bash
# 1. Установите зависимости
cd tests/load
pip install -r requirements.txt

# 2. Запустите Control Plane (в отдельном терминале)
cd ../../control-plane
uvicorn main:app --reload

# 3. Запустите Locust
locust -f locustfile.py --host=http://localhost:8000
```

Откройте http://localhost:8089 для веб-интерфейса Locust.

## Типы пользователей

| Класс | Описание | Вес |
|-------|----------|-----|
| `HealthCheckUser` | Мониторинг — легкие запросы к `/health` | 3 |
| `APIUser` | Обычные пользователи API | 5 |
| `AggressiveUser` | Агрессивный трафик (симуляция атаки) | 2 |
| `AttackModeUser` | Тестирование режима защиты | 1 |

## Режимы запуска

### Интерактивный (с Web UI)
```bash
locust -f locustfile.py --host=http://localhost:8000
```

### Headless (без UI)
```bash
# 100 пользователей, 10 новых в секунду, 60 секунд
locust -f locustfile.py --host=http://localhost:8000 \
    --headless -u 100 -r 10 -t 60s
```

### Spike Test (симуляция всплеска)
```bash
locust -f locustfile.py --host=http://localhost:8000 \
    --headless --master
```

## Метрики

После теста Locust покажет:
- **RPS** — запросов в секунду
- **Latency** — время отклика (p50, p95, p99)
- **Failures** — количество ошибок
- **Users** — активные пользователи

## Расширение

Добавьте новые сценарии в `locustfile.py`:

```python
class CustomUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def my_test(self):
        self.client.get("/my-endpoint")
```
