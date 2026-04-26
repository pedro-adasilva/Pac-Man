# Informe de estado del proyecto Pac-Man

Fecha: 2026-04-26
Repositorio: /home/pedro/42/cursus/pac_man

## 1) Objetivo y estado general
Proyecto de Pac-Man en Python (pygame + wheel externo `mazegenerator`) con entrada principal:

- `python3 pac-man.py config.json`

# Estado actual

- Arranque desde menú funcionando con `ENTER` (incluye keypad enter).
- Opción de salida desde menú con `Q` funcionando.
- Regreso a menú tras `game_over` sin regeneración inmediata del laberinto.
- Generación de laberintos usando exclusivamente el wheel externo (sin fallback local).
- Gestión de errores de generación mostrando pantalla de error y permitiendo salir con `Q`/`ESC`.
- Lint y typing en verde.
- Carga del laberinto en hilo de fondo para no congelar la UI al pulsar `ENTER`.
- Movimiento constante con dirección persistente: el jugador empieza quieto y avanza hasta pared o cambio de dirección.
- Pacgums y super-pacgums implementados: spawn, render, recogida, puntuación y fin de nivel al consumirlos todos.

## 2) Cambios importantes ya aplicados

### Flujo de juego y menú
- Se eliminó la carga inicial de laberinto en `__init__` para evitar esperas al entrar al menú.
- El laberinto se carga al pulsar `ENTER` en estado menú.
- En menú se acepta tanto:
  - `pygame.K_RETURN`
  - `pygame.K_KP_ENTER`
- `Q` en menú cierra la aplicación.
- Se añadió una pantalla de carga con texto animado mientras el laberinto se genera.
- `Q` cierra el juego en cualquier estado (`menu`, `loading`, `playing`, `game_over`, `error`).

### Regreso rápido al menú
- Al terminar nivel (`game_over`), volver al menú ya no dispara generación de laberinto.
- Esto evitó el retraso de varios segundos al volver al menú.

### Política de generación (requisito de sujeto)
- Se eliminó toda ruta de fallback en `maze_provider.py`.
- Si la generación falla o expira timeout, se lanza error explícito.
- No se construyen laberintos alternativos fuera de `MazeGenerator` del wheel.

### Manejo de Ctrl+C y procesos hijos
- Se ajustó la ruta de `KeyboardInterrupt` para evitar trazas ruidosas del proceso hijo durante cierre.
- Si la interrupción ocurre esperando `join`, se termina el hijo limpiamente y se propaga la interrupción.

### Seeds y estabilidad de generación
- Se detectó que algunos seeds tardan demasiado (timeout de 5s) y disparan error.
- Para modo “aleatorio” (config `seed: 0`) se implementó selección desde un pool de seeds seguros/rápidos:
  - `(1, 2, 8, 45, 55, 59, 60, 62, 69, 77)`
- Se aumentó el timeout del generador a `7.0s`.
- Se limitó el número de reintentos para evitar pantallas de carga demasiado largas.
- Objetivo: mantener variedad sin caer en timeout frecuente.

### Pacgums y puntuación
- Se generan pacgums en la mayoría de celdas caminables, excluyendo entrada y salida.
- Se colocan super-pacgums cerca de las 4 esquinas del laberinto.
- Se eliminan al pasar el jugador por su celda.
- Los puntos usan la configuración:
  - `points_per_pacgum`
  - `points_per_super_pacgum`
- HUD muestra el score y el total de pacgums restantes.

## 3) Archivos clave tocados
- `src/pacman/game.py`
- `src/pacman/maze_provider.py`
- `config.json`
- `informe` de handoff actualizado en `informes/`

## 4) Configuración actual relevante
En `config.json`:

- `levels[0].seed = 0` para activar selección de seed segura aleatoria.
- Tamaño actual: `21x21`.
- `pacgum = 42`.
- `points_per_pacgum = 10`.
- `points_per_super_pacgum = 50`.

## 5) Validaciones realizadas

- `make lint` (flake8 + mypy): OK.
- Pruebas unitarias (`pytest`): OK (suite actual pequeña).
- Pruebas de comportamiento manual/controlado:
  - Entrada con `ENTER` y `KP_ENTER`.
  - Salida con `Q`.
  - Flujo de error de generación.
  - Variación de laberintos: en 8 ejecuciones se observaron 4 laberintos únicos.
  - Pacgums: al recoger un pacgum aumenta la puntuación.
  - Super-pacgums: al recoger uno aumenta la puntuación.
  - Fin de nivel al consumir todos los coleccionables.
  - `Q` global en `menu`, `loading`, `playing`, `game_over` y `error`.

## 6) Incidencias conocidas / contexto técnico

- El wheel `mazegenerator` tiene seeds que pueden tardar mucho para 21x21 y producir timeout.
- Con la política “sin fallback”, un timeout debe mostrarse como error (comportamiento actual correcto según requisito).
- La calidad de “aleatoriedad” está condicionada por el pool de seeds seguros para evitar bloqueos/timeout.
- El juego todavía no implementa la parte final del subject: vidas, fantasmas, progresión multi-nivel real, name entry, highscores en menú, pausa y temporizador visible.

## 7) Trabajo pendiente (alto nivel)

1. Sistema de vidas y condiciones de derrota.
2. Fantasmas (spawn, movimiento/IA básica, colisiones).
3. Progresión multi-nivel (usar toda la lista `levels`).
4. Entrada de nombre al finalizar partida.
5. Persistencia y visualización de highscores en menú.
6. Uso de `level_max_time` y temporizador en HUD.
7. Pausa y reanudación durante la partida.

## 8) Recomendaciones para el siguiente agente

1. Mantener estrictamente la regla: no introducir fallback de laberintos.
2. Si aparecen más timeouts, priorizar:
   - ampliar o recalibrar la lista de seeds rápidos según el tamaño del mapa,
   - o reducir reintentos si la pantalla de carga se percibe larga,
   siempre sin generar laberintos fuera del wheel.
3. Al tocar flujo de estados, validar siempre:
   - menú -> playing,
   - game_over -> menú inmediato,
   - error -> salida con `Q`/`ESC`.
4. Para la próxima fase, el orden más natural es:
   - vidas + colisiones con fantasmas,
   - progresión multi-nivel,
   - highscores y name entry,
   - temporizador y pausa.
4. Ejecutar al cerrar cambios:
   - `make lint`
   - `PYTHONPATH=src .venv/bin/pytest -q`

## 9) Comandos útiles

- Instalar entorno: `make install`
- Ejecutar juego: `make run`
- Lint + type check: `make lint`
- Tests: `PYTHONPATH=src .venv/bin/pytest -q`

---
Informe generado para handoff entre agentes.
