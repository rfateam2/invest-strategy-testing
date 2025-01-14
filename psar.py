import yfinance as yf
import pandas as pd
import ta
from datetime import datetime

def get_psar(ticker):
    try:
        # Задаем диапазон дат
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - pd.Timedelta(days=365)).strftime("%Y-%m-%d")

        # Загружаем данные
        data = yf.download(ticker, start=start_date, end=end_date, interval="1d")

        # Проверка на пустые данные
        if data.empty:
            raise ValueError(f"Не удалось загрузить данные для тикера {ticker}.")

        # Вывод отладочной информации
        # print("Первые строки загруженных данных:")
        # print(data.head())
        # print("\nСтолбцы данных перед обработкой:", data.columns)

        # Обработка MultiIndex
        if isinstance(data.columns, pd.MultiIndex):
            print("\nMultiIndex обнаружен, объединяю уровни индексов.")
            data.columns = [col[0] for col in data.columns]
            #print("Столбцы данных после обработки MultiIndex:", data.columns)

        # Проверка наличия необходимых столбцов
        if not {"High", "Low", "Close"}.issubset(data.columns):
            print("\nДанные после обработки:")
            print(data.head())
            raise ValueError("Данные не содержат необходимых столбцов 'High', 'Low', 'Close'.")

        # Проверяем, есть ли пустые значения
        if data[["High", "Low", "Close"]].isnull().any().any():
            raise ValueError("Данные содержат пустые значения в столбцах 'High', 'Low' или 'Close'.")

        # Рассчитываем Parabolic SAR
        psar_indicator = ta.trend.PSARIndicator(
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            step=0.02,
            max_step=0.2
        )
        data["PSAR"] = psar_indicator.psar()

        # Проверяем рассчитанный PSAR
        if data["PSAR"].isnull().all():
            raise ValueError("Недостаточно данных для расчета PSAR.")
        
        # Получаем последнее значение
        last_psar = data["PSAR"].iloc[-1]
        last_close = data["Close"].iloc[-1]

        return {"Ticker": ticker, "Close": last_close, "PSAR": last_psar}

    except Exception as e:
        print(f"Ошибка: {e}")
        return None


# Вызов функции
if __name__ == "__main__":
    result = get_psar("QQQ")
    if result:
        print(f"Последнее значение PSAR для {result['Ticker']}: {result['PSAR']}")
        print(f"Цена закрытия: {result['Close']}")
