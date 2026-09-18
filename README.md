# AMRAS — Adaptive Market-Regime Algorithmic System

Bot de trading cuantitativo institucional, escrito en Python 3.11+, con
arquitectura orientada a objetos, modular y **agnóstica a la plataforma**:
puede conectarse a cualquier exchange de criptoactivos soportado por
[CCXT](https://github.com/ccxt/ccxt) (Binance, Bybit, KuCoin, OKX, Kraken...)
cambiando una sola variable de entorno, y deja la estructura lista para
brokers tradicionales (MetaTrader 5, Interactive Brokers).

> ⚠️ **Disclaimer**: el trading algorítmico conlleva riesgo real de pérdida
> de capital. Este proyecto es una base de arquitectura de software; antes
> de operar con dinero real, valida exhaustivamente cada módulo con
> backtesting, papel/sandbox y auditoría de riesgo propia.

## Arquitectura

```
                     ┌───────────────────────┐
                     │   REGIME-SWITCHING     │   ADX / ATR / Bollinger BW
                     │        ENGINE          │──► TREND | RANGE | COMPRESSION
                     └───────────┬───────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
      ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
      │ Trend-Following│  │ Mean-Reversion │  │   Breakout    │
      │  MA Crossover  │  │  RSI Channel   │  │ Pending Stops │
      └───────┬───────┘  └───────┬───────┘  └───────┬───────┘
              └──────────────────┼──────────────────┘
                                 ▼
                     ┌───────────────────────┐
                     │      RISK ENGINE       │   sizing · R:R · BE · trailing
                     │  (multilevel, ATR-based)│   daily kill switch (-X%)
                     └───────────┬───────────┘
                                 ▼
                     ┌───────────────────────┐
                     │    ORDER MANAGER       │   slippage / fees / latency log
                     └───────────┬───────────┘
                                 ▼
                     ┌───────────────────────┐
                     │ BaseExchangeConnector  │   universal adapter contract
                     │  CCXT · MT5* · IB*     │   (*stubs, ready to implement)
                     └───────────────────────┘
```

## Estructura de carpetas

```
config/           Configuración tipada (settings.py) y logging
  settings.py       Carga .env -> Settings (pydantic-settings)
  logging_config.py Logger de aplicación + logger de ejecución (audit trail)

core/             Motor de dominio (agnóstico a exchange y a estrategia concreta)
  enums.py          MarketRegime, OrderSide/Type/Status, SignalAction, PositionSide
  models.py         Candle, Signal, OrderRequest/Result, Position
  indicators.py     ATR, ADX, RSI, SMA/EMA, Bollinger bandwidth
  regime_engine.py  Clasificador de régimen de mercado (Regime-Switching Engine)
  risk_manager.py   Position sizing, R:R, break-even, trailing stop, kill switch
  order_manager.py  Orquesta el envío de órdenes + logging de ejecución
  engine.py         AmrasEngine: orquestador principal (ciclo de decisión)

strategies/       Motores tácticos (uno por régimen de mercado)
  base_strategy.py    Contrato abstracto BaseStrategy
  trend_following.py  MA Crossover + filtro ADX (activo en TENDENCIA)
  mean_reversion.py   RSI + canal de precio (activo en RANGO)
  breakout.py         Órdenes stop pendientes en niveles clave (activo en COMPRESIÓN)

connectors/       Capa de abstracción universal multi-exchange/broker
  base_connector.py  BaseExchangeConnector (ABC): get_balance, get_ticker,
                      create_order, cancel_order, get_historical_klines
  ccxt_connector.py  Implementación CCXT (Binance, Bybit, KuCoin, OKX, Kraken...)
  mt5_connector.py   Stub para MetaTrader 5 (misma interfaz, sin implementar)
  ib_connector.py    Stub para Interactive Brokers (misma interfaz, sin implementar)
  factory.py         build_connector(): selecciona el conector según EXCHANGE_NAME
  exceptions.py       Jerarquía de errores de dominio (Network, Auth, Order, ...)

tests/            Suite pytest (regime engine, risk manager, estrategias, conectores)
logs/             amras.log (aplicación) y execution.log (auditoría de órdenes)
main.py           Punto de entrada: arma el motor y corre el loop principal
```

## Instalación

```bash
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edita .env con tus claves de API y parámetros de estrategia/riesgo
```

## Cambiar de exchange/broker

Todo pasa por una única variable en `.env`:

```bash
EXCHANGE_NAME=binance     # o bybit, kucoin, okx, kraken, bitget, gateio, mexc...
```

`connectors/factory.py` resuelve automáticamente el conector CCXT
correspondiente. Ningún otro módulo del sistema conoce el nombre del
exchange: todo el código de `core/` y `strategies/` habla únicamente contra
`BaseExchangeConnector`.

Para brokers tradicionales (`EXCHANGE_NAME=mt5` o `interactive_brokers`) la
fábrica ya enruta a `MT5Connector` / `IBConnector`; son stubs con la misma
interfaz, listos para implementarse contra la API del terminal/broker
correspondiente sin tocar el resto del sistema.

## Ejecución

```bash
python main.py
```

El loop principal, para cada símbolo en `SYMBOLS`:
1. Descarga las últimas velas OHLCV.
2. Clasifica el régimen de mercado (`RegimeEngine`).
3. Gestiona la posición abierta (si existe): break-even, trailing stop, SL/TP.
4. Si no hay posición, delega en la estrategia mapeada a ese régimen.
5. Valida la señal contra el Risk Engine (R:R mínimo, kill switch diario).
6. Dimensiona y envía la orden a través del `OrderManager`.

Se detiene limpiamente con `Ctrl+C` (SIGINT) o `SIGTERM`.

## Tests

```bash
pytest
```

Cubre: clasificación de régimen con series sintéticas, sizing de posición,
validación de R:R, break-even/trailing, kill switch por drawdown diario,
generación de señales por estrategia, y la fábrica de conectores.

## Próximas fases

- **Fase 2 — Dashboard de control**: interfaz web (panel `AMRAS Quantitative
  Trading System`, estilo glassmorphism cian/verde sobre fondo oscuro,
  paneles de Trend-Following / Mean-Reversion / Breakout, Risk Shield
  central, matriz de órdenes pendientes y estado del sistema en vivo)
  consumiendo este motor vía una API REST/WebSocket.
- **Fase 3 — Backtesting**: motor de backtesting vectorizado reutilizando
  `RegimeEngine`, `RiskManager` y las estrategias tal cual, sobre datos
  históricos.
- **Fase 4 — Conectores nativos**: implementación real de `MT5Connector`
  e `IBConnector`.
