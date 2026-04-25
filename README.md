# Pac-Man (Python)

Base inicial para el proyecto de Pac-Man con generacion de laberintos usando el wheel proporcionado.

## Requisitos

- Python 3.10+
- Entorno virtual recomendado

## Setup rapido

```bash
make install
```

`make install` crea automaticamente `.venv` e instala dependencias dentro de ese entorno.

Si quieres tener el entorno activo tambien en tu shell interactiva:

```bash
source .venv/bin/activate
```

## Ejecutar

```bash
make run
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

- ENTER: iniciar partida desde menu / volver al menu tras game over
- WASD o flechas: mover jugador
- N: completar nivel instantaneamente (si `cheat_mode` esta activo)

## Estructura

- `src/pacman/main.py`: punto de entrada
- `src/pacman/game.py`: bucle principal y estados de UI
- `src/pacman/maze_provider.py`: adaptador de `mazegenerator`
- `src/pacman/settings.py`: carga de configuracion `jsonc`
- `src/pacman/highscores.py`: persistencia de highscores
- `config/game_config.jsonc`: configuracion editable
