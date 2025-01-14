# python test_advince_psar.py QQQ 100 2024-01-01 --end_date 2024-12-31

import yfinance as yf
import ta
import pandas as pd
import numpy as np
import argparse
from datetime import datetime
import matplotlib.pyplot as plt
import os

import yfinance as yf
import pandas as pd

def load_data(ticker, start_date, end_date):
    """
    Загрузить данные для заданного тикера и диапазона дат.
    
    Аргументы:
        ticker (str): Тикер инструмента.
        start_date (str): Дата начала в формате 'YYYY-MM-DD'.
        end_date (str): Дата окончания в формате 'YYYY-MM-DD'.
    
    Возвращает:
        DataFrame: Данные с колонками 'Date', 'Close', 'High', 'Low' и 'DayOfWeek'.
    """
    # Загрузка данных с помощью yfinance
    data = yf.download(ticker, start=start_date, end=end_date, interval="1d")
    
    # Проверка на пустые данные
    if data.empty:
        raise ValueError(f"Не удалось загрузить данные для тикера {ticker}. Проверьте тикер и диапазон дат.")
    
    # Сброс индекса и переименование столбцов
    data.reset_index(inplace=True)
    data.rename(columns={"Date": "Date", "Close": "Close", "High": "High", "Low": "Low"}, inplace=True)
    
    # Преобразование столбца Date в формат datetime
    data["Date"] = pd.to_datetime(data["Date"], errors='coerce')
    
    # Проверка на некорректные даты
    if data["Date"].isnull().any():
        raise ValueError("Столбец 'Date' содержит некорректные значения.")
    
    # Формируем конечный DataFrame
    data = data[["Date", "Close", "High", "Low"]]
    data["DayOfWeek"] = data["Date"].dt.day_name()
    
    return data

def apply_test_strategy_with_psar(data, weekly_investment, multiplier, day_of_week):
    total_invested = 0
    total_units = 0
    max_price = 0
    portfolio_value = []
    monthly_investments = []

    for _, row in data.iterrows():
        date, close, day_name, psar = row["Date"], row["Close"], row["DayOfWeek"], row["PSAR"]
        max_price = max(max_price, close)

        # Проверяем условие покупки на основе PSAR
        if day_name == day_of_week and close > psar:
            total_units += weekly_investment / close
            total_invested += weekly_investment
            monthly_investments.append((date.strftime("%Y-%m"), weekly_investment))

        portfolio_value.append(total_units * close)

    return total_invested, portfolio_value, pd.DataFrame(monthly_investments, columns=["YearMonth", "Investment"])

def calculate_parabolic_sar(data):
    """Рассчитать Parabolic SAR на основе недельного периода."""
    # Проверяем, что данные содержат необходимые столбцы
    if not {"High", "Low", "Close", "Date"}.issubset(data.columns):
        raise ValueError("Данные должны содержать столбцы 'High', 'Low', 'Close' и 'Date' для расчета PSAR.")

    # Добавляем неделю в данные
    data["Week"] = data["Date"].dt.to_period("W").dt.to_timestamp()
    weekly_data = data.groupby("Week").agg(
        {"Close": "last", "High": "max", "Low": "min"}
    ).reset_index()

    # Расчет PSAR
    psar_indicator = ta.trend.PSARIndicator(
        high=weekly_data["High"],
        low=weekly_data["Low"],
        close=weekly_data["Close"],
        step=0.02,
        max_step=0.2,
    )
    weekly_data["PSAR"] = psar_indicator.psar()

    # Присоединяем к исходным данным
    data = data.merge(weekly_data[["Week", "PSAR"]], how="left", left_on="Date", right_on="Week")
    data["PSAR"].fillna(method="ffill", inplace=True)
    return data

def main():
    parser = argparse.ArgumentParser(description="Тестирование инвестиционных стратегий.")
    parser.add_argument("ticker", type=str, help="Тикер акции (например, QQQ).")
    parser.add_argument("weekly_investment", type=float, help="Сумма еженедельного пополнения в долларах.")
    parser.add_argument("start_date", type=str, help="Дата начала периода (YYYY-MM-DD).")
    parser.add_argument("--end_date", type=str, default=datetime.now().strftime("%Y-%m-%d"), help="Дата конца периода (YYYY-MM-DD).")
    parser.add_argument("--day_of_week", type=str, default="Friday", help="День недели для еженедельного пополнения.")
    parser.add_argument("--multiplier", type=float, default=1.5, help="Множитель для дополнительных инвестиций.")
    args = parser.parse_args()

    try:
        data = load_data(args.ticker, args.start_date, args.end_date)
        print(data.head())  # Убедитесь, что столбцы 'High', 'Low', 'Close', 'Date' присутствуют
    except ValueError as e:
        print(f"Ошибка: {e}")
        
    data = calculate_parabolic_sar(data) # Рассчитать PSAR

    # Применение стратегий
    simple_invested, simple_values, simple_monthly = apply_simple_strategy(data, args.weekly_investment, args.day_of_week)
    total_units_simple = simple_invested / data["Close"].iloc[0]

    # Вычисление метрик
    simple_end_value = simple_values[-1] if simple_values else 0


    # Вывод результатов в консоль
    print(f"\n=== Простая стратегия ===")
    print(f"Сумма стандартного недельного пополнения: ${args.weekly_investment:.2f}")
    print(f"Общая сумма вложений: ${simple_invested:.2f}")
    print(f"Итоговая стоимость портфеля: ${simple_end_value:.2f}")
    print(f"Итоговая прибыль: ${simple_end_value - simple_invested:.2f}")

    psar_data = calculate_parabolic_sar(data)
    print("\n=== Parabolic SAR (недельный) ===")
    print(psar_data.head())

if __name__ == "__main__":
    main()