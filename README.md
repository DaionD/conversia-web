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

     AmrasEngine publishes every cycle into ──► core/state.py (EngineState)
                                                        │
                                                        ▼
                                           api/app.py — FastAPI REST + WebSocket
                                          (reads the latest snapshot only; never
                                           calls the exchange on a client request)
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

api/              Capa API (FastAPI): expone el estado del motor por REST/WebSocket
  schemas.py         Modelos Pydantic de respuesta (contrato público de la API)
  converters.py       Traduce los modelos de dominio (core/models.py) a schemas
  engine_runner.py    Corre AmrasEngine en un hilo de fondo, publica en EngineState
  app.py              Endpoints REST + WebSocket /ws/stream

tests/            Suite pytest (regime engine, risk manager, estrategias, conectores,
                  EngineState, endpoints de la API)
logs/             amras.log (aplicación) y execution.log (auditoría de órdenes)
main.py           Punto de entrada CLI: arma el motor y corre el loop principal
api_main.py       Punto de entrada API: levanta el servidor FastAPI (uvicorn)
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

## API (Fase 3)

La capa API expone el estado del motor por REST y WebSocket, para que
`dashboard.html` (u otro cliente) lo consuma sin hablar nunca directamente
con el exchange.

```bash
python api_main.py
# equivalente a: uvicorn api.app:app --host 0.0.0.0 --port 8000
```

Por defecto (`API_RUN_ENGINE=false` en `.env.example`) la API levanta sin
motor de trading real: todos los endpoints responden, pero el estado está
vacío. Esto permite probar la API y el dashboard sin credenciales de
exchange. Cuando `EXCHANGE_NAME`/`API_KEY`/`API_SECRET` estén listos
(sandbox o real), pon `API_RUN_ENGINE=true` y la API arranca `AmrasEngine`
en un hilo de fondo (`api/engine_runner.py`) que publica cada ciclo en
`core/state.py` (`EngineState`, protegido por lock). Los endpoints solo
leen ese snapshot en memoria — ninguna petición HTTP llama al exchange, así
que la latencia de la API es independiente de la latencia del exchange. Si
el conector falla (red, credenciales inválidas), el ciclo se registra como
error en `EngineState` y el bucle sigue vivo, listo para el próximo ciclo.

**Endpoints:**

| Método | Ruta                    | Descripción                                   |
|--------|-------------------------|------------------------------------------------|
| GET    | `/api/health`           | Estado del proceso + si el hilo del motor vive |
| GET    | `/api/status`           | Algoritmos/feed/broker online, kill switch      |
| GET    | `/api/portfolio`        | Equity actual                                   |
| GET    | `/api/regime`           | Régimen de mercado por símbolo                  |
| GET    | `/api/positions`        | Posiciones abiertas + PnL no realizado           |
| GET    | `/api/signals/recent`   | Últimas señales generadas por las estrategias    |
| GET    | `/api/orders/recent`    | Últimas órdenes ejecutadas (slippage, fees, latencia) |
| WS     | `/ws/stream`             | Snapshot completo cada `WS_BROADCAST_INTERVAL_SECONDS` |

Documentación interactiva (Swagger) en `http://localhost:8000/docs` una vez
levantado el servidor.

> `dashboard.html` sigue usando datos simulados en el navegador por ahora;
> conectarlo a estos endpoints (reemplazando `MarketFeed` por `fetch`/`WebSocket`
> contra `/api/...` y `/ws/stream`) es el siguiente paso natural.

## Tests

```bash
pytest
```

Cubre: clasificación de régimen con series sintéticas, sizing de posición,
validación de R:R, break-even/trailing, kill switch por drawdown diario,
generación de señales por estrategia, la fábrica de conectores, `EngineState`
y los endpoints de la API (con el hilo del motor desactivado, sin red real).

## Estado del proyecto por fases

- ✅ **Fase 1 — Motor**: arquitectura core, estrategias, risk engine, conectores.
- ✅ **Fase 2 — Dashboard**: `dashboard.html`, panel visual con datos simulados.
- ✅ **Fase 3 — API**: capa REST/WebSocket (`api/`) sobre `EngineState`.
- ⬜ **Fase 3b — Integración**: conectar `dashboard.html` a la API real en vez
  de la simulación en el navegador.
- ⬜ **Fase 4 — Backtesting**: motor de backtesting vectorizado reutilizando
  `RegimeEngine`, `RiskManager` y las estrategias tal cual, sobre datos
  históricos.
- ⬜ **Fase 5 — Conectores nativos**: implementación real de `MT5Connector`
  e `IBConnector`.
