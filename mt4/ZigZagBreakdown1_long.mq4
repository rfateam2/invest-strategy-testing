//+------------------------------------------------------------------+
//|                                           ZigZagBreakdown1.mq4   |
//|                             Copyright 2025, Your Name            |
//|                                              https://example.com|
//+------------------------------------------------------------------+
#property copyright "2025, Your Name"
#property link      "https://example.com"
#property version   "1.00"
#property strict

// Входные параметры
input int InpDepth=12;          // Depth для ZigZag
input int InpDeviation=5;       // Deviation для ZigZag
input int InpBackstep=3;        // Backstep для ZigZag
input int MAPeriod=70;          // Период Moving Average
input double LotSize=0.1;       // Размер позиции (лоты)
input double StopLossPercent=1.0; // Процент для стоп-лосса (оптимизируемый)
input int Slippage=3;           // Максимальное проскальзывание в пунктах

// Глобальные переменные
double lastPeakValue = 0.0;     // Последний верхний пик ZigZag (A)
double lastLowPeakValue = 0.0;  // Последний нижний пик ZigZag (B)
bool signalBuyTriggered = false;// Флаг для сигнала на покупку
double maValue;                 // Значение MA70

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                   |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
}

//+------------------------------------------------------------------+
//| Expert tick function                                               |
//+------------------------------------------------------------------+
void OnTick()
{
   // Рассчитываем MA70
   maValue = iMA(NULL, 0, MAPeriod, 0, MODE_SMA, PRICE_CLOSE, 0);

   // Вычисляем уровни ZigZag
   CalculateZigZagLevels();

   // Условие для покупки
   bool aboveMA = Close[0] > maValue;
   bool breakoutA = High[0] > lastPeakValue && lastPeakValue != 0.0 && !signalBuyTriggered;

   // Проверка открытых позиций
   if(OrdersTotal() == 0 && aboveMA && breakoutA)
   {
      // Уровни для входа и выхода
      double entryPrice = Ask;                  // Цена входа
      double levelA = lastPeakValue;            // Уровень A
      double levelB = lastLowPeakValue;         // Уровень B
      double levelC = levelA + (levelA - levelB); // Уровень C (тейк-профит)
      double levelF = levelB - (levelA - levelB) / 2; // Уровень F
      double stopLoss = levelF - (levelB * StopLossPercent / 100); // Стоп-лосс

      // Открытие позиции на покупку
      int ticket = OrderSend(Symbol(), OP_BUY, LotSize, entryPrice, Slippage, 
                            stopLoss, levelC, "ZigZag Breakdown 1 Buy", 0, 0, clrGreen);
      
      if(ticket < 0)
         Print("OrderSend failed with error #", GetLastError());
      else
      {
         Print("Order opened successfully, ticket #", ticket);
         signalBuyTriggered = true; // Устанавливаем флаг после открытия
      }
   }
}

//+------------------------------------------------------------------+
//| Функция расчёта уровней ZigZag                                   |
//+------------------------------------------------------------------+
void CalculateZigZagLevels()
{
   int i, limit, counterZ, whatlookfor = 0;
   int back, pos, lasthighpos = 0, lastlowpos = 0;
   double extremum;
   double curlow = 0.0, curhigh = 0.0, lasthigh = 0.0, lastlow = 0.0;
   double highBuffer[], lowBuffer[];
   
   ArrayResize(highBuffer, Bars);
   ArrayResize(lowBuffer, Bars);
   ArrayInitialize(highBuffer, 0.0);
   ArrayInitialize(lowBuffer, 0.0);

   limit = Bars - InpDepth;

   for(i = limit; i >= 0; i--)
   {
      // Поиск минимума
      extremum = Low[iLowest(NULL, 0, MODE_LOW, InpDepth, i)];
      if(extremum == lastlow)
         extremum = 0.0;
      else
      {
         lastlow = extremum;
         if(Low[i] - extremum > InpDeviation * Point)
            extremum = 0.0;
         else
         {
            for(back = 1; back <= InpBackstep; back++)
            {
               pos = i + back;
               if(pos < Bars && lowBuffer[pos] != 0 && lowBuffer[pos] > extremum)
                  lowBuffer[pos] = 0.0;
            }
         }
      }
      if(Low[i] == extremum)
         lowBuffer[i] = extremum;
      else
         lowBuffer[i] = 0.0;

      // Поиск максимума
      extremum = High[iHighest(NULL, 0, MODE_HIGH, InpDepth, i)];
      if(extremum == lasthigh)
         extremum = 0.0;
      else
      {
         lasthigh = extremum;
         if(extremum - High[i] > InpDeviation * Point)
            extremum = 0.0;
         else
         {
            for(back = 1; back <= InpBackstep; back++)
            {
               pos = i + back;
               if(pos < Bars && highBuffer[pos] != 0 && highBuffer[pos] < extremum)
                  highBuffer[pos] = 0.0;
            }
         }
      }
      if(High[i] == extremum)
         highBuffer[i] = extremum;
      else
         highBuffer[i] = 0.0;
   }

   // Определение последних пиков
   for(i = limit; i >= 0; i--)
   {
      switch(whatlookfor)
      {
         case 0:
            if(lastlow == 0.0 && lasthigh == 0.0)
            {
               if(highBuffer[i] != 0.0)
               {
                  lasthigh = High[i];
                  lasthighpos = i;
                  whatlookfor = -1;
                  lastPeakValue = lasthigh;
               }
               if(lowBuffer[i] != 0.0)
               {
                  lastlow = Low[i];
                  lastlowpos = i;
                  whatlookfor = 1;
                  lastLowPeakValue = lastlow;
               }
            }
            break;
         case 1:
            if(lowBuffer[i] != 0.0 && lowBuffer[i] < lastlow && highBuffer[i] == 0.0)
            {
               lastlowpos = i;
               lastlow = lowBuffer[i];
               lastLowPeakValue = lastlow;
            }
            if(highBuffer[i] != 0.0 && lowBuffer[i] == 0.0)
            {
               lasthigh = highBuffer[i];
               lasthighpos = i;
               whatlookfor = -1;
               lastPeakValue = lasthigh;
               signalBuyTriggered = false;
            }
            break;
         case -1:
            if(highBuffer[i] != 0.0 && highBuffer[i] > lasthigh && lowBuffer[i] == 0.0)
            {
               lasthighpos = i;
               lasthigh = highBuffer[i];
               lastPeakValue = lasthigh;
               signalBuyTriggered = false;
            }
            if(lowBuffer[i] != 0.0 && highBuffer[i] == 0.0)
            {
               lastlow = lowBuffer[i];
               lastlowpos = i;
               whatlookfor = 1;
               lastLowPeakValue = lastlow;
            }
            break;
      }
   }
}

//+------------------------------------------------------------------+