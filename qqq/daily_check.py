

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
import json

# Функция для загрузки данных
def load_data(ticker, start_date, end_date):
    data = yf.download(ticker, start=start_date, end=end_date)
    if data.empty:
        raise ValueError(f"No data available for {ticker}.")
    return data

# Функция для получения текущей цены
def get_current_price(ticker):
    stock = yf.Ticker(ticker)
    try:
        # Пытаемся получить текущую цену
        current_price = stock.history(period="1d", interval="1m")["Close"].iloc[-1]
    except:
        # Если рынок закрыт, берем цену закрытия последнего бара
        current_price = stock.history(period="1d")["Close"].iloc[-1]
    return current_price

# Функция для загрузки/сохранения состояния
def load_state(filename="strategy_state.json"):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {"max_price": 0.0, "last_action": None}

def save_state(state, filename="strategy_state.json"):
    with open(filename, 'w') as f:
        json.dump(state, f)

# Основная логика стратегии
def apply_strategy():
    # Параметры
    ticker_1 = "QQQ"  # Основной тикер
    ticker_2 = "QLD"  # Тикер для 10-20% просадки
    ticker_3 = "TQQQ" # Тикер для >20% просадки
    index = "QQQ"     # Базовый тикер для просадки
    start_date = "2020-01-01"  # Начальная дата для данных
    end_date = datetime.now().strftime("%Y-%m-%d")
    dropdown_1 = 0.10  # 10% просадка
    dropdown_2 = 0.20  # 20% просадка

    # Загрузка данных
    data = load_data(index, start_date, end_date)
    current_price = get_current_price(index)

    # Загрузка состояния
    state = load_state()
    max_price = max(state["max_price"], current_price)  # Обновляем максимум
    state["max_price"] = max_price

    # Логика стратегии
    recommendations = []
    if current_price >= max_price * (1 - dropdown_1):
        recommendations.append(f"Покупка {ticker_1} (QQQ) по цене ${current_price:.2f}")
    elif current_price >= max_price * (1 - dropdown_2) and current_price < max_price * (1 - dropdown_1):
        recommendations.append(f"Покупка {ticker_2} (QLD) по цене ${current_price:.2f}")
        if state["last_action"] != "sold":
            recommendations.append(f"Продажа {ticker_1} (QQQ) если не проданы")
    else:  # current_price < max_price * (1 - dropdown_2)
        recommendations.append(f"Покупка {ticker_3} (TQQQ) по цене ${current_price:.2f}")

    # Сохранение состояния
    state["last_action"] = "buy" if recommendations[0].startswith("Покупка") else "sold" if "Продажа" in recommendations else state["last_action"]
    save_state(state)

    # Вывод рекомендаций
    print(f"Текущая дата: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Текущая цена {index}: ${current_price:.2f}")
    print(f"Максимальная цена: ${max_price:.2f}")
    print("Рекомендации:")
    for rec in recommendations:
        print(f"- {rec}")

if __name__ == "__main__":
    try:
        apply_strategy()
    except Exception as e:
        print(f"Произошла ошибка: {e}")