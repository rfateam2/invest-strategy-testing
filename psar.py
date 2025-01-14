# python test_advince_psar.py QQQ 100 2024-01-01 --end_date 2024-12-31

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


if __name__ == "__main__":
    ticker = "QQQ"
    start_date = "2024-01-01"
    end_date = "2024-12-31"

    try:
        data = load_data(ticker, start_date, end_date)
        print(data.head())  # Вывод первых строк данных
    except ValueError as e:
        print(f"Ошибка: {e}")

    data = calculate_parabolic_sar(data)