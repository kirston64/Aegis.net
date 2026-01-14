# 🛡️ Aegis.net

**Современная Anti-DDoS защита для малого бизнеса и игровых серверов**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-MVP-orange.svg)]()

---

## 🚀 Что такое Aegis.net?

Aegis.net — это open-source платформа защиты от DDoS-атак, созданная с фокусом на:

- **🎮 Игровые серверы** — нативная поддержка GTA 5 RP, Minecraft, CS2
- **💼 Малый бизнес** — простая настройка, понятные цены
- **🔍 Прозрачность** — полный доступ к логам и аналитике

## ✨ Ключевые преимущества

| Функция | Описание |
|---------|----------|
| **Smart Shield AI** | Адаптивная защита с 5 уровнями, автоматическое определение атак |
| **L3/L4 Protection** | eBPF/XDP фильтрация на скорости линии (10Gbps+) |
| **L7 Protection** | Rust + OpenResty WAF с минимальной задержкой |
| **Game-Aware** | Понимание игровых протоколов (RAGE MP, Source, Minecraft) |
| **Real-time Dashboard** | Визуализация атак в реальном времени |

## 📁 Структура проекта

```
aegis.net/
├── website/          # Лендинг и документация
├── control-plane/    # Python API (FastAPI)
│   ├── api/          # REST API
│   └── workers/      # Background tasks
├── dashboard/        # React веб-интерфейс
├── edge/             # Edge-компоненты
│   ├── xdp/          # eBPF/XDP фильтры
│   ├── proxy/        # Rust L7 прокси
│   └── openresty/    # Lua WAF правила
└── docs/             # Документация
```

## 🛠️ Быстрый старт

### Требования

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Redis

### Установка

```bash
# Клонирование
git clone https://github.com/kirston64/Aegis.net.git
cd Aegis.net

# Control Plane
cd control-plane
pip install -r requirements.txt
uvicorn api.main:app --reload

# Dashboard
cd ../dashboard
npm install
npm run dev
```

## 📊 Тарифы

| Тариф | Цена | Что включено |
|-------|------|--------------|
| **Free** | €0/мес | 1 домен, 1M запросов, базовая защита |
| **Pro** | €19/мес | 5 доменов, 50M запросов, полная защита |
| **Business** | €79/мес | 25 доменов, 500M запросов, приоритетная поддержка |

## 🤝 Контрибуция

Мы приветствуем contributions! См. [CONTRIBUTING.md](docs/CONTRIBUTING.md).

## 📄 Лицензия

MIT License — см. [LICENSE](LICENSE)

---

**Aegis.net** — Защита, которой можно доверять. 🛡️
