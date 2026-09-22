# Production Sync — 2026-09-23

Source reviewed: production commit `dd9c79c` (`Add Archivebound RPG experience`).

The production folder was inspected read-only. Its `config/config.json` mode
selection was intentionally not copied into the Sandbox.

## Changes carried into the Sandbox

- Added **Out of Spec: The Archivist Trials** (Archivebound), including its Qt
  frontend package, narrative, state model, persistence, level definition, and game
  window.
- Added the complete RPG font, sprite, environment, combat, dialogue, puzzle,
  cinematic, and quest asset set.
- Added the Archivebound Shop reward at 2,500 XP and extended the existing game
  launcher to open either Tetris or Archivebound.
- Added the production narrative, dialogue-review, voice, and visual-canon documents.
- Added the RPG asset preparation, normalization, preview, and dialogue-export tools.
- Added the complete Archivebound regression suite.

## Modular boundary

This production change does not alter router-mode selection, row scope, Selenium
dispatch, or form routing. Archivebound remains under `frontend/rpg/`; its only shared
application integration points are `frontend/pyqt_dialogs.py` and
`utils/rewards.py`. Both integration files exactly match production commit
`dd9c79c` after the sync.

## Integrity and validation

- All 245 files added by the production commit are present and byte-for-byte
  identical in the Sandbox.
- Python AST validation passed for 145 application and test files.
- Archivebound suite: 136 tests passed.
- Existing non-RPG suite: 419 tests passed.
- Combined offline coverage: 555 tests passed.
- No live IRT/Selenium routing was performed.
- The controlled MNSUTB Source Detail remains exactly
  `Table-(5-day spec source)`.

