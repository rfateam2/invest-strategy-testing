//+------------------------------------------------------------------+
//|                                           ZigZagBreakdownEA.mq4  |
//|                             Copyright 2025, Your Name            |
//|                                              https://example.com|
//+------------------------------------------------------------------+
#property copyright "2025, Your Name"
#property link      "https://example.com"
#property version   "1.00"
#property strict

// Input parameters
input int Depth=12;             // ZigZag Depth
input int Deviation=5;          // ZigZag Deviation
input int Backstep=3;           // ZigZag Backstep
input int MAPeriod=70;          // Moving Average Period
input bool UseMAFilter=false;   // Use MA Filter (default: false)
input double StopLossPercent=1.0; // Stop Loss Percent
input double LotSize=0.1;       // Position Size (Lots)
input int Slippage=3;           // Slippage (Points)

// Global variables
double lastHighPeak = 0.0;      // Last High peak (Level A)
double lastLowPeak = 0.0;       // Last Low peak (Level B)
bool signalBuyTriggered = false;// Flag for buy signal
bool signalSellTriggered = false;// Flag for sell signal

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   if(Backstep >= Depth)
   {
      Print("Backstep cannot be greater or equal to Depth");
      return(INIT_FAILED);
   }
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
   if(OrdersTotal() > 0) return;

   CalculateZigZagLevels();

   double maValue = UseMAFilter ? iMA(NULL, 0, MAPeriod, 0, MODE_SMA, PRICE_CLOSE, 0) : 0.0;
   double prevAsk = iOpen(NULL, 0, 1); // Предыдущая цена открытия как аппроксимация Ask
   double prevBid = iOpen(NULL, 0, 1); // Предыдущая цена открытия как аппроксимация Bid

   // Buy condition: Ask crosses above lastHighPeak
   bool maBuyCondition = UseMAFilter ? Ask > maValue : true;
   bool buyCross = (prevAsk <= lastHighPeak && Ask > lastHighPeak);
   if(maBuyCondition && buyCross && lastHighPeak != 0.0 && !signalBuyTriggered)
   {
      double entryPrice = Ask;
      double levelA = lastHighPeak;
      double levelB = lastLowPeak;
      double takeProfit = levelA + (levelA - levelB);
      double levelF = levelB - (levelA - levelB) / 2;
      double stopLoss = levelF - (levelB * StopLossPercent / 100);

      int ticket = OrderSend(Symbol(), OP_BUY, LotSize, entryPrice, Slippage, 
                            stopLoss, takeProfit, "ZigZagBreakdown Buy", 0, 0, clrGreen);
      
      if(ticket < 0)
         Print("Buy OrderSend failed with error #", GetLastError());
      else
         signalBuyTriggered = true;
   }

   // Sell condition: Bid crosses below lastLowPeak
   bool maSellCondition = UseMAFilter ? Bid < maValue : true;
   bool sellCross = (prevBid >= lastLowPeak && Bid < lastLowPeak);
   if(maSellCondition && sellCross && lastLowPeak != 0.0 && !signalSellTriggered)
   {
      double entryPrice = Bid;
      double levelA = lastHighPeak;
      double levelB = lastLowPeak;
      double takeProfit = levelB - (levelA - levelB);
      double levelF = levelA + (levelA - levelB) / 2;
      double stopLoss = levelF + (levelA * StopLossPercent / 100);

      int ticket = OrderSend(Symbol(), OP_SELL, LotSize, entryPrice, Slippage, 
                            stopLoss, takeProfit, "ZigZagBreakdown Sell", 0, 0, clrRed);
      
      if(ticket < 0)
         Print("Sell OrderSend failed with error #", GetLastError());
      else
         signalSellTriggered = true;
   }
}

//+------------------------------------------------------------------+
//| Function to calculate ZigZag levels and signals                  |
//+------------------------------------------------------------------+
void CalculateZigZagLevels()
{
   int i, limit, back;
   double extremum;
   double HighBuffer[];
   double LowBuffer[];

   ArrayResize(HighBuffer, Bars);
   ArrayResize(LowBuffer, Bars);
   ArrayInitialize(HighBuffer, 0.0);
   ArrayInitialize(LowBuffer, 0.0);

   limit = Bars - Depth;

   for(i = limit; i >= 0; i--)
   {
      extremum = Low[iLowest(NULL, 0, MODE_LOW, Depth, i)];
      if(Low[i] == extremum)
      {
         for(back = 1; back <= Backstep && (i + back) < Bars; back++)
         {
            if(LowBuffer[i + back] != 0 && LowBuffer[i + back] > extremum)
               LowBuffer[i + back] = 0.0;
         }
         LowBuffer[i] = extremum;
      }
      else
         LowBuffer[i] = 0.0;

      extremum = High[iHighest(NULL, 0, MODE_HIGH, Depth, i)];
      if(High[i] == extremum)
      {
         for(back = 1; back <= Backstep && (i + back) < Bars; back++)
         {
            if(HighBuffer[i + back] != 0 && HighBuffer[i + back] < extremum)
               HighBuffer[i + back] = 0.0;
         }
         HighBuffer[i] = extremum;
      }
      else
         HighBuffer[i] = 0.0;
   }

   bool lastWasHigh = false;
   for(i = limit; i >= 0; i--)
   {
      if(HighBuffer[i] != 0.0)
      {
         lastHighPeak = High[i];
         signalBuyTriggered = false;
         lastWasHigh = true;
      }
      else if(LowBuffer[i] != 0.0)
      {
         lastLowPeak = Low[i];
         signalSellTriggered = false;
         lastWasHigh = false;
      }
   }
}

//+------------------------------------------------------------------+