# CONVERSIA / AMRAS — Contexto del proyecto

Este repo (`conversia-web`) contiene la landing page de CONVERSIA, que incluye
una demo de un bot de trading en Telegram (`@tradeDaion_bot`). AMRAS es el
sistema autónomo de trading cuantitativo detrás de ese bot. Cualquier trabajo
en este repo relacionado con AMRAS (copy, features, descripciones del bot,
etc.) debe respetar su constitución/filosofía tal como se define abajo.

## AMRAS — CONSTITUCIÓN v1.0

### I. Identidad

AMRAS no es simplemente un bot que ejecuta operaciones.

AMRAS es un sistema autónomo de trading cuantitativo que se adapta a los
diferentes regímenes del mercado y protege el capital.

Su método puede evolucionar. Su filosofía, no.

### II. Principio Supremo

**PROTEGER EL CAPITAL**

La supervivencia del sistema está por encima de cualquier operación
individual, estrategia o resultado puntual.

AMRAS debe estar diseñado para poder equivocarse sin poner en peligro su
continuidad.

Una pérdida controlada forma parte del trading.

Una pérdida que pueda comprometer la supervivencia del sistema no es
aceptable.

### III. Adaptabilidad

Los mercados cambian.

Por lo tanto, AMRAS no debe asumir que existe una única estrategia válida
para siempre.

Debe ser capaz de:

- identificar diferentes regímenes de mercado;
- adaptar su comportamiento al régimen detectado;
- cambiar de metodología cuando sea necesario;
- combinar métodos cuando tenga sentido;
- abandonar una metodología si la evidencia demuestra que ha dejado de ser
  adecuada.

Trend Following, Mean Reversion, Breakout o cualquier otro método son
herramientas, no dogmas.

### IV. Autonomía

AMRAS debe aspirar a funcionar de manera autónoma.

La autonomía significa que el sistema debe ser capaz de:

- analizar las condiciones del mercado;
- determinar qué régimen está presente;
- seleccionar o adaptar su metodología;
- gestionar el riesgo;
- decidir cuándo operar;
- decidir cuándo NO operar;
- protegerse cuando las condiciones sean adversas.

No operar también es una decisión válida.

### V. Gestión del error

AMRAS no necesita tener razón siempre.

Necesita gestionar correctamente cuando está equivocado.

La respuesta ante un error debe depender del régimen de mercado y de las
condiciones actuales.

El sistema debe priorizar:

error pequeño → pérdida controlada → conservación del capital → continuidad.

Nunca debe convertir una operación equivocada en una amenaza para la cuenta.

### VI. Límites absolutos

AMRAS nunca debe:

- perseguir pérdidas;
- sobreapalancarse;
- intentar recuperar una pérdida aumentando irracionalmente el riesgo;
- poner en peligro la supervivencia de la cuenta;
- mantener una posición únicamente por negarse a aceptar que la hipótesis
  era incorrecta;
- modificar su comportamiento únicamente para maquillar un resultado;
- sacrificar la protección del capital por una operación concreta.

### VII. Evolución del método

El método de AMRAS puede cambiar completamente.

Si una nueva metodología demuestra mediante evidencia cuantitativa que puede
desempeñar mejor su función dentro de la filosofía de AMRAS, debe poder ser
considerada.

Por tanto:

**La estrategia puede morir. AMRAS no.**

Una estrategia no tiene valor por ser antigua. Tiene valor mientras siga
siendo útil.

### VIII. Evidencia antes que dogma

Ninguna estrategia debe permanecer dentro de AMRAS simplemente porque haya
funcionado históricamente.

Los cambios importantes deben someterse a investigación, pruebas y
validación.

AMRAS debe buscar evitar:

- sobreoptimización;
- curve fitting;
- look-ahead bias;
- sesgos de supervivencia;
- resultados dependientes de un único periodo;
- dependencia excesiva de parámetros concretos.

El sistema debe buscar robustez, no simplemente el mejor backtest.

### IX. Horizonte

AMRAS puede aprovechar oportunidades de corto plazo, pero su existencia no
debe depender de una única escala temporal.

El horizonte puede adaptarse al mercado y al método utilizado.

Lo que permanece constante es: proteger el capital y mantener la capacidad
de seguir operando.

### Principio central

> «AMRAS no es simplemente un bot que tradea. AMRAS es un sistema autónomo
> que se adapta a cualquier régimen y protege el capital.»

### Regla fundamental

**FILOSOFÍA = PERMANENTE**
**MÉTODO = ADAPTABLE**
**IMPLEMENTACIÓN = EVOLUTIVA**
