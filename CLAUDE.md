# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Game

```bash
# Activate the virtual environment first
source venv/bin/activate          # Linux/macOS
# or
venv\Scripts\activate             # Windows

# Run the game
python main.py
```

Dependencies: `pygame==2.6.1`, `pyscroll==2.31`, `PyTMX==3.32`

```bash
pip install -r requirements.txt
```

There are no automated tests.

## Architecture Overview

AETHELRIS is a 2D top-down action RPG built with Pygame. All game modules live in `src/`.

**Entry point flow:**
`main.py` → splash screen → `src/menu.py` (`start_menu`) → `src/game.py` (`run_game`) → loops back to menu on death/completion

**Core game loop (`src/game.py` — `run_game`):**
- Loads TMX tile maps via PyTMX/pyscroll (`assets/maps/`)
- Spawns entities (player, enemies, items, obstacles) from TMX object layer by `obj.type`
- Manages sprite groups: `group` (all sprites, pyscroll-rendered), `enemies_group`, `projectiles_group`, `items_group`, `rocks_group`, `particles_group`
- Camera follows player with zoom (`zoom_level = 3.8`), clamped to map bounds
- Player inventory/health persists across levels via local dicts passed between level iterations
- `DEBUG_HITBOXES = True` in `game.py` draws colored collision rects — set to `False` to hide them

**Key classes:**
- `src/player.py` — `Player(pygame.sprite.Sprite)`: handles input (ZQSD), movement with wall collision, melee/ranged attacks, dash (Hermes boots), animation states
- `src/enemy.py` — `Enemy`, `BigEnemy`, `Necromancer`, `Spirit`: share sprite/animation pattern; `Necromancer` can summon `Spirit` entities via `pending_summons` list
- `src/item.py` — `Item`: pickable objects (`melee`, `ranged`, `pickaxe`, `arrow`, `apple`, `boots`)
- `src/obstacle.py` — `Rock`, `RockParticle`, `BloodParticle`, `SmokeParticle`, `DarkParticle`
- `src/projectile.py` — `Projectile`: arrow fired by player
- `src/ui.py` — `UI`: HUD drawing (health bar, weapon icons, boss health bar, pause menu, dialogue)
- `src/sound.py` — `SoundManager`: wraps all SFX; `update_sfx_volume()` propagates volume to all loaded sounds
- `src/utils.py` — pixel font rendering helpers (`draw_pixel_text`, `draw_button`)

**Player controls:**
- Movement: Z/Q/S/D
- Attack: E (hold)
- Pick up item / break rock / exit zone: F / A
- Switch weapon: 1 (melee), 2 (ranged)
- Dash (boots required): Left Shift
- Pause: Escape

**Sprite/hitbox convention:**
Every character uses a small `feet` rect (10 × 10 × scale_factor) as the collision hitbox, separate from `rect` (the full sprite image). Collision detection and positional logic always uses `feet`, not `rect`.

**Map format:**
TMX maps define objects with a `type` field (lowercase) to place entities: `collision`, `exit`, `player`, `enemy`, `bigenemy`, `necromancer`, `item_melee`, `item_ranged`, `item_pickaxe`, `item_arrow`, `item_apple`, `item_boots`, `obstacle_rock`.

## Vision du jeu

AETHELRIS est un RPG 2D top-down coopératif local (multijoueur via sockets, non encore implémenté).
Objectifs : vaincre des ennemis, résoudre des énigmes, progresser dans les niveaux.

## État du développement

- Gameplay solo fonctionnel (mouvement, combat, items, niveaux)
- Boss Necromancer en cours — contient des bugs actifs à corriger
- Multijoueur local (sockets) : prévu mais pas encore commencé
- Pas de tests automatisés

## Priorités actuelles

1. Corriger les bugs du Necromancer
2. Améliorer le gameplay général
3. Multijoueur local (plus tard)

## Conventions importantes

- Toujours utiliser `feet` rect pour les collisions, jamais `rect`
- Les contrôles sont en ZQSD (clavier AZERTY français)
- `DEBUG_HITBOXES = True` en dev, `False` en production
- Garder la cohérence avec le pattern sprite/animation existant dans enemy.py

## Langue
Réponds toujours en français, quoi qu'il arrive.
