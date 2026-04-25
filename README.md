# Pac-Man (Python)

Juego Pac-Man completo en Python usando generación de laberintos mediante el paquete externo A-Maze-ing.

## Requisitos

- Python 3.10+
- Entorno virtual recomendado

## Setup rápido

```bash
make install
```

`make install` crea automáticamente `.venv` e instala dependencias dentro de ese entorno.

## Ejecutar

```bash
make run
# O directamente:
python3 pac-man.py config.json
```

## Debug

```bash
make debug
```

## Lint y typing

```bash
make lint
# opcional
make lint-strict
```

## Controles base

- ENTER: iniciar partida desde menú / volver al menú tras game over
- WASD o flechas: mover jugador
- N: completar nivel instantaneamente (si `cheat_mode` está activo)

## Configuración

El archivo `config.json` controla todos los parámetros del juego:

- **window_width, window_height, fps**: Parámetros de ventana
- **lives**: Vidas iniciales (default: 3)
- **pacgum, points_per_pacgum**: Cantidad y puntos por goma
- **points_per_super_pacgum**: Puntos por super goma (default: 50)
- **points_per_ghost**: Puntos por fantasma comido (default: 200)
- **level_max_time**: Tiempo máximo por nivel (default: 90s)
- **levels**: Array de niveles con width, height, seed, num_ghosts
- **highscores_file**: Ruta del archivo de highscores persistentes
- **cheat_mode**: Activar modo cheat (N para ganar instantáneamente)

Soporta comentarios JSON (líneas con `#`).

## Estructura

- `pac-man.py`: punto de entrada principal
- `src/pacman/main.py`: módulo de entrada (deprecado, usa pac-man.py directamente)
- `src/pacman/game.py`: bucle principal y estados de UI
- `src/pacman/maze_provider.py`: adaptador de `mazegenerator` con protección de timeout
- `src/pacman/settings.py`: carga de configuración JSON con clamp a defaults seguros
- `src/pacman/highscores.py`: persistencia de highscores con validación de nombres
- `config.json`: configuración editable con comentarios

## Sistema de Highscores

- Validación de nombres: máx 10 caracteres, solo alfanuméricos y espacios
- Persistencia en JSON
- Top 10 scores guardados automáticamente
- Entrada de nombre tras terminar la partida (win o lose)
- Visualización en menú principal
