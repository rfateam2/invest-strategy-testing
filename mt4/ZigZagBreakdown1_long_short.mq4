//+------------------------------------------------------------------+
//|                                           ZigZagBreakdown1.mq4   |
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
input double LotSize=0.1;       // Position Size (Lots)
input double StopLossPercent=1.0; // Stop Loss Percent (Optimizable)
input int Slippage=3;           // Slippage (Points)

// Global variables
double lastHighPeak = 0.0;      // Last High peak of ZigZag (Level A)
double lastLowPeak = 0.0;       // Last Low peak of ZigZag (Level B)
bool signalBuyTriggered = false;// Flag for buy signal
bool signalSellTriggered = false;// Flag for sell signal
double maValue;                 // MA70 value

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
   // Calculate MA70
   maValue = iMA(NULL, 0, MAPeriod, 0, MODE_SMA, PRICE_CLOSE, 0);

   // Calculate ZigZag levels
   CalculateZigZagLevels();

   // Long conditions
   bool aboveMA = Close[0] > maValue;
   bool breakoutLong = High[0] > lastHighPeak && lastHighPeak != 0.0 && !signalBuyTriggered;

   // Short conditions
   bool belowMA = Close[0] < maValue;
   bool breakoutShort = Low[0] < lastLowPeak && lastLowPeak != 0.0 && !signalSellTriggered;

   // Check open positions
   if(OrdersTotal() == 0)
   {
      // Long entry
      if(aboveMA && breakoutLong)
      {
         double entryPrice = Ask;
         double levelA = lastHighPeak;
         double levelB = lastLowPeak;
         double levelC = levelA + (levelA - levelB); // Take-profit
         double levelF = levelB - (levelA - levelB) / 2; // Protective level
         double stopLoss = levelF - (levelB * StopLossPercent / 100);

         int ticket = OrderSend(Symbol(), OP_BUY, LotSize, entryPrice, Slippage, 
                               stopLoss, levelC, "ZigZag Breakdown 1 Buy", 0, 0, clrGreen);
         
         if(ticket < 0)
            Print("Buy OrderSend failed with error #", GetLastError());
         else
         {
            Print("Buy order opened, ticket #", ticket);
            signalBuyTriggered = true;
         }
      }

      // Short entry
      if(belowMA && breakoutShort)
      {
         double entryPrice = Bid;
         double levelA = lastHighPeak;
         double levelB = lastLowPeak;
         double levelC = levelB - (levelA - levelB); // Take-profit
         double levelF = levelA + (levelA - levelB) / 2; // Protective level for short
         double stopLoss = levelF + (levelA * StopLossPercent / 100);

         int ticket = OrderSend(Symbol(), OP_SELL, LotSize, entryPrice, Slippage, 
                               stopLoss, levelC, "ZigZag Breakdown 1 Sell", 0, 0, clrRed);
         
         if(ticket < 0)
            Print("Sell OrderSend failed with error #", GetLastError());
         else
         {
            Print("Sell order opened, ticket #", ticket);
            signalSellTriggered = true;
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Function to calculate ZigZag levels                              |
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

   limit = Bars - Depth;

   for(i = limit; i >= 0; i--)
   {
      // Find low
      extremum = Low[iLowest(NULL, 0, MODE_LOW, Depth, i)];
      if(extremum == lastlow)
         extremum = 0.0;
      else
      {
         lastlow = extremum;
         if(Low[i] - extremum > Deviation * Point)
            extremum = 0.0;
         else
         {
            for(back = 1; back <= Backstep; back++)
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

      // Find high
      extremum = High[iHighest(NULL, 0, MODE_HIGH, Depth, i)];
      if(extremum == lasthigh)
         extremum = 0.0;
      else
      {
         lasthigh = extremum;
         if(extremum - High[i] > Deviation * Point)
            extremum = 0.0;
         else
         {
            for(back = 1; back <= Backstep; back++)
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

   // Determine last peaks
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
                  lastHighPeak = lasthigh;
               }
               if(lowBuffer[i] != 0.0)
               {
                  lastlow = Low[i];
                  lastlowpos = i;
                  whatlookfor = 1;
                  lastLowPeak = lastlow;
               }
            }
            break;
         case 1:
            if(lowBuffer[i] != 0.0 && lowBuffer[i] < lastlow && highBuffer[i] == 0.0)
            {
               lastlowpos = i;
               lastlow = lowBuffer[i];
               lastLowPeak = lastlow;
               signalSellTriggered = false;
            }
            if(highBuffer[i] != 0.0 && lowBuffer[i] == 0.0)
            {
               lasthigh = highBuffer[i];
               lasthighpos = i;
               whatlookfor = -1;
               lastHighPeak = lasthigh;
               signalBuyTriggered = false;
            }
            break;
         case -1:
            if(highBuffer[i] != 0.0 && highBuffer[i] > lasthigh && lowBuffer[i] == 0.0)
            {
               lasthighpos = i;
               lasthigh = highBuffer[i];
               lastHighPeak = lasthigh;
               signalBuyTriggered = false;
            }
            if(lowBuffer[i] != 0.0 && highBuffer[i] == 0.0)
            {
               lastlow = lowBuffer[i];
               lastlowpos = i;
               whatlookfor = 1;
               lastLowPeak = lastlow;
               signalSellTriggered = false;
            }
            break;
      }
   }
}

//+------------------------------------------------------------------+