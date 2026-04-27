# Pac-Man (Python)

Juego Pac-Man completo en Python usando generación de laberintos mediante el paquete externo A-Maze-ing.

## Requisitos


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


## Configuración

El archivo `config.json` controla todos los parámetros del juego:

# Pac-Man Python

A complete, playable Pac-Man game implementation in Python 3.10+ using Pygame and object-oriented programming principles. This project demonstrates robust software engineering practices including modular architecture, configuration management, persistent highscores, and comprehensive error handling.

## Features

- **Complete Game Implementation**: Full Pac-Man gameplay with multiple levels, ghosts, and collectibles
- **Configurable Gameplay**: JSON-based configuration with comment support for customizing game parameters
- **Persistent Highscores**: JSON-based highscore system storing top 10 scores with player names
- **Robust Error Handling**: Graceful handling of configuration errors, maze generation failures, and runtime issues
- **Modular Architecture**: Separable concerns for game logic, rendering, AI, and configuration
- **Smooth Animations**: Interpolated movement for fluid player and ghost animations
- **Cheat Mode**: Enabled via configuration for easier peer review and testing
- **Multiple Levels**: Support for 10+ distinct levels with progressive difficulty

## Requirements

- Python 3.10 or later
- pip or compatible package manager
- Virtual environment (recommended: venv or conda)

### Dependencies

- pygame>=2.5.2
- commentjson>=0.9.0
- flake8>=7.0.0 (development)
- mypy>=1.10.0 (development)
- pytest>=8.0.0 (development)

A-Maze-ing package (wheel provided): mazegenerator-00001-py3-none-any.whl

## Installation

### Using Make

```bash
make install
```

This will create a virtual environment and install all dependencies.

### Manual Installation

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
pip install ./mazegenerator-00001-py3-none-any.whl
```

## Usage

### Running the Game

```bash
make run
# or
python3 pac-man.py config.json
```

The game requires a valid JSON configuration file. A `config.json` is provided with default settings.

### Debug Mode

```bash
make debug
# Runs the game with Python debugger (pdb)
```

### Cleaning Build Artifacts

```bash
make clean
# Removes __pycache__, .mypy_cache, and .pytest_cache
```

### Code Quality

```bash
make lint
# Runs flake8 and mypy with standard checks

make lint-strict
# Runs flake8 and mypy with strict mode enabled
```

## Configuration

The game uses a JSON configuration file (default: `config.json`) with support for both standard JSON and C/C++ style comments.

### Configuration Structure

```json
{
	"# Window settings": "",
	"window_width": 1280,          // Game window width in pixels
	"window_height": 960,          // Game window height in pixels
	"fps": 60,                     // Frames per second

	"# Game mechanics": "",
	"lives": 3,                    // Starting number of lives
	"pacgum": 42,                  // Number of small dots to collect
	"points_per_pacgum": 10,       // Points for eating a pacgum
	"points_per_super_pacgum": 50, // Points for eating a power pellet
	"points_per_ghost": 200,       // Points for eating a ghost
	"level_max_time": 90,          // Time limit per level in seconds

	"# Level generation": "",
	"levels": [
		{
			"width": 21,               // Maze width in tiles
			"height": 21,              // Maze height in tiles
			"seed": 0,                 // Seed for maze generation (0 = random)
			"num_ghosts": 1            // Number of ghosts in this level
		}
	],

	"# Persistent data": "",
	"highscores_file": "data/highscores.json",  // Path to highscores storage
	"cheat_mode": false            // Enable cheat features (debug mode)
}
```

### Configuration Validation

- Missing or invalid values are clamped to safe defaults
- Unknown keys are silently ignored
- Errors are logged to stderr but do not crash the game
- Window dimensions are clamped to reasonable ranges (480x360 - 2560x1440)
- Game values (lives, scores, time) are validated and clamped

## How to Play

### Main Menu

- **ENTER**: Start a new game
- **Q**: Quit the game

### In-Game Controls

- **Arrow Keys or WASD**: Move Pac-Man through the maze
- **P**: Pause/Resume game (when implemented)
- **Q**: Return to main menu

### Gameplay Objectives

1. **Collect all pacgums** (small dots) to complete a level
2. **Avoid ghosts** - touching a ghost costs one life
3. **Collect power pellets** (large dots in corners) to temporarily make ghosts edible
4. **Eat edible ghosts** for bonus points (200 points each)
5. **Complete all levels** to win the game

### Scoring

- **Pacgum**: 10 points (configurable)
- **Power Pellet**: 50 points (configurable)
- **Ghost**: 200 points (configurable)

### Lives and Game Over

- Start with 3 lives (configurable)
- Lose a life when touched by a ghost
- Respawn at center of maze after losing a life
- Game Over when all lives are lost
- Victory when all levels are completed

## Project Architecture

### Module Structure

```
src/pacman/
├── __init__.py           # Package initialization
├── main.py              # Entry point for package import
├── game.py              # Main game loop and state machine
├── settings.py          # Configuration loading and validation
├── models.py            # Data classes for game state
├── rendering.py         # Pygame rendering functions
├── maze_provider.py     # Integration with A-Maze-ing package
├── ghost_logic.py       # Ghost AI and collision detection
├── level_flow.py        # Level setup and progression
└── highscores.py        # Highscore management
```

### Key Classes

#### `Game`
Main game controller managing the game loop, state transitions, and coordinate player/ghost/collectible updates.

#### `GameRuntime`
Dataclass holding mutable runtime state (position, score, state).

#### `GhostRuntime`
Dataclass for individual ghost state (position, direction, color, spawn point).

#### `GameSettings`
Frozen dataclass with immutable game configuration loaded from JSON.

#### `MazeLevel`
Generated maze data including grid, entry/exit points, and shortest path.

### Game States

- `menu`: Main menu waiting for player input
- `loading`: Maze generation in progress (non-blocking via thread)
- `playing`: Active gameplay
- `game_over`: End state with score and outcome
- `error`: Maze generation or fatal error occurred

### Rendering Pipeline

The rendering system uses Pygame for graphics and supports multiple UI layers:

1. **Background**: Dark theme for visibility
2. **Maze**: Walls drawn as outlines, corridors as empty spaces
3. **Collectibles**: Pacgums and super-pacgums as circles
4. **Player**: Pac-Man as filled ellipse at center position
5. **Ghosts**: Colored circles at ghost positions
6. **HUD**: Score, lives, level, and collectible counter

All coordinates are smoothly interpolated between tile positions for fluid animation.

### Ghost AI

Ghosts use a simple chase behavior:

- Compute available moves from current position
- Prefer moves toward player
- Use Manhattan distance for pathfinding
- Track recent cells to avoid getting stuck
- Respawn at spawn point when eaten

## Development

### Code Quality

This project adheres to strict Python standards:

- **Python 3.10+**: Modern syntax with type hints
- **PEP 257**: Google-style docstrings for all public and private methods
- **Type Hints**: Complete type annotations for mypy strict mode
- **Flake8**: Consistent code style and linting

### Running Tests

```bash
pytest tests/
```

### Type Checking

```bash
PYTHONPATH=src mypy src tests --disallow-untyped-defs --check-untyped-defs
```

## Highscores

### Storage Format

Highscores are stored in JSON format (default: `data/highscores.json`):

```json
[
	{
		"name": "ALICE",
		"score": 5000
	},
	{
		"name": "BOB",
		"score": 4500
	}
]
```

### Player Name Validation

- Maximum 10 characters
- Alphanumeric characters and spaces only
- Special characters are stripped
- Falls back to "PLAYER" if empty

### Highscore System Features

- Top 10 scores automatically maintained
- Loaded at game start, saved at game end
- Robust to file errors (missing or corrupted files)
- Automatic directory creation when saving

## Cheat Mode

Enable via `config.json` (`"cheat_mode": true`):

- **N key** (when enabled): Skip current level and gain 500 bonus points
- **Invincibility**: When enabled, ghosts cannot eat the player
- Use for testing and peer review

## Error Handling

The game implements comprehensive error handling:

- **Configuration Errors**: Missing or invalid files logged with clear messages
- **Maze Generation Failures**: Retries with different seeds, shows error message on final failure
- **Runtime Exceptions**: Caught and logged without traceback
- **File I/O Errors**: Gracefully handled for highscores and configuration

## Deployment

This project is ready for deployment to gaming platforms:

- Self-contained package with all dependencies
- Cross-platform compatible (Windows, macOS, Linux)
- No external services required
- Portable configuration system

## Development Status

### Implemented

- ✅ Core gameplay loop with multiple levels
- ✅ Configurable game parameters
- ✅ Persistent highscores
- ✅ Robust error handling
- ✅ Modular architecture
- ✅ Smooth animations
- ✅ Ghost AI
- ✅ Multiple collectible types
- ✅ Code quality standards (type hints, docstrings, linting)

### Planned Features

- 🔄 Pause menu with resume and main menu options
- 🔄 Highscores viewer in main menu
- 🔄 Instructions screen
- 🔄 Super-pacgum mechanics (ghost edibility mode)
- 🔄 Time-based level limits
- 🔄 Additional cheat mode features

## Author

Created by 42 School student as part of the curriculum.
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
