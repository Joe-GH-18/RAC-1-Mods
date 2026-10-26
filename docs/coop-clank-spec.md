# Co-op Clank: "Player 2 is Clank" (implementation spec)

Status: **design**, written 2026-10-26 from `NOTES.md`, the mods' sources and a static read of the
executable. Nothing in here has been run yet. Facts marked *(NOTES)* are confirmed in earlier
sessions. Facts marked *(static)* were read from the code today and must be confirmed live before
anything is built on them.

This file is for the agent that builds the mod. Read it whole, then `README.md`,
`mods/__init__.py`, `mods/game.py`, the top of `mods/goldenclank.py` and `mods/clank.py`, and the
sections *Hero*, *Mobys*, *Damage*, *Pad and movement*, *Clank* and *Golden Clank* of
`NOTES.md`. Keep `NOTES.md` up to date in its own style as you go (dated entries; say whether a
thing was *seen by me* or *confirmed by the user*).

---

## 0. The pitch, and what the video needs

The game is called Ratchet **&** Clank, yet in Ratchet & Clank 1 Clank is a backpack for the whole
game. This mod makes the title literal. Plug in a second controller and **Clank jumps off
Ratchet's back and becomes Player 2**. He flies on his thruster wings, zaps enemies with a
lightning beam, dive-punches like Secret Agent Clank, and docks back onto Ratchet. When both
players own Golden Clank, they **pilot Giant Clank together**: Player 1 drives the legs, Player 2
fires the arms. With no second player, the same Clank can fight on his own (the "Clank Zapper that
doesn't suck").

Why this order of priorities: the channel's audience asked for it ("Imagine if this was the Clank
Zapper instead", the top comment under the Golden Clank video), and co-op mods for single-player
classics are breaking out on tiny channels right now (FF XII co-op 87k views on 1.4k subscribers,
RE4 2005 co-op 36k on 580, RE Code Veronica recomp with online co-op 21k on 155). **Build what
the camera sees first.** The video needs these moments; everything else is secondary:

1. **"PLAYER 2 JOINED":** Clank leaps off Ratchet's back mid-fight, wings snap open, he zaps
   a robot. This is the first 5 seconds of the video.
2. **Two players clearing a room**, Clank flying circles around Ratchet.
3. **Overcharge:** a chain of lightning jumping across a whole group of enemies.
4. **Shock-Wrench combo:** Ratchet's wrench and Clank's zap on the same enemy, a gold burst.
5. **Two pilots, one Giant Clank:** the climax.
6. **Ratchet can't glide without Clank.** Clank has to dock for the jump (co-op platforming).
   Optional, see the open questions.

Online play needs no netcode. With Parsec or similar, the host shares the screen and the guest's
controller appears as RPCS3's Player 2. Say so in the README and the video.

---

## 1. Ground rules of this repository

- Game: Ratchet & Clank 1 HD, **NPEA00385**, under RPCS3 on Linux. Mods are PPC assembly templates
  in Python (`parts()`), assembled by `build.py` with keystone into the code cave, hooking game
  instructions (`hooks()` → `game.Hook`). Read `mods/__init__.py` for the module contract.
- **One mod, one module:** `mods/coop.py` (or a package `mods/coop/` if it grows past ~1500
  lines; `goldenclank.py` is 6k lines in one file, so a package is better here: `__init__.py`,
  `pad.py`, `body.py`, `flight.py`, `combat.py`, `team.py`, `ai.py`, `hud.py`). `NAME = "coop"`,
  `TITLE = "Co-op Clank"`. Add it to `MODS` in `mods/__init__.py` **after** `goldenclank`.
- **Mods don't call each other.** Where co-op and Golden Clank must cooperate (the tag-team), they
  share words in the state block declared in `mods/game.py` (section 3.2), and each mod works
  alone when the other is not built in (the shared words are then always 0).
- Several mods hooking the same instruction must all use `chain=True` (see `game.Hook`). A `jump`
  hook cannot be chained. If you need a site another mod has as a jump hook, make it a shared
  chained site in `game.py` and adapt both mods.
- **No game data in the repository.** Clank's model comes from the player's own RC1 data at patch
  time, like Giant Clank's (`rc2data.py`, `mods/rc2.py`'s `Extract`).
- Every user-visible change gets an in-game check. Where feel is involved (speeds, damage, the
  pop-off), ask the user to confirm and record their words in `NOTES.md`.
- Commits: one per working step, message style as in `git log` ("Co-op: Clank leaves the backpack").

### Known traps (from NOTES; each one froze or crashed the game once)

- Never rewrite a linked joint manipulator's moby field (`S_J_MOBY`, +8 links) live. It made a ring
  and froze the game.
- `JOINT_POSITION`'s joint numbers are not bone numbers (joint 76 crashed it). Use the model's joint
  list (model +0x1c).
- Clamp animation frames: a frame past the last one crashed the game.
- Keep eulers wrapped to -π..π (an unwrapped turn made a spawned bomb stretch across the screen).
- A model's sound definitions play only where their bank is loaded. Foreign models' sounds crashed
  the sound update (0x15be68), which is why `giant_model()` strips them.
- On death and respawn, joint manipulator lists and joint effects slots can end up as rings
  (the Golden Clank death freeze). Anything the mod keeps on Ratchet's or Clank's mobys must be
  reset on respawn and level load.
- Help messages only show when Options → HelpDesk → Text (`0x71fb59`) is on.
- Only one `tools/peek.py` user at a time.

---

## 2. Player-facing spec

### 2.1 Modes

| Mode | When | What Clank does |
|---|---|---|
| **Docked** | default; always in Clank-only and Giant-Clank-only sections | on Ratchet's back as in the game |
| **Player 2** | P2 presses Start or X on controller 2 | P2 flies and fights; Ratchet unchanged |
| **AI** | chosen in the pause menu, no P2 present | Clank leaves on his own, follows, fights (section 2.6) |

A new item on the pause menu's Gadgets page, **"Clank Zapper"**, cycles Off / AI. The pattern is
the Charge Boots item in `mods/chargeboots/menu.py`. Player 2 always overrides AI. Store the
choice in an unused save byte and document it in the module docstring. The Weapon levels and
Golden Clank use the ammunition array's spare words: pick another unused word and check it with a
save made before the mod.

### 2.2 Joining, leaving, docking

- **Join:** with controller 2 connected, P2 presses **Start** or **X**. Ratchet stays in control.
  Clank does a 0.5 s pop-off: he leaps up and back off Ratchet's back (arc 1.2 up, 0.8 back),
  the thruster wings snap open, a gold burst (`BURST` puffs as in Golden Clank), a sound, and the
  message **"PLAYER 2 JOINED"**.
- **Dock:** P2 holds **Select** for 0.7 s, or flies within 1.2 of Ratchet's back and presses
  **Triangle**. Clank is pulled in over 0.25 s with a magnetic "clack" (gold puffs at the seat).
  Message "CLANK DOCKED". Energy refills fast while docked.
- **Undock again:** Start or X, as joining.
- **Controller 2 disconnected** (its +0x9c flag 0 for 2 s): Clank docks by himself.
- **Suspended** (Clank docks at once and joining is ignored) while:
  - Ratchet is not the hero: hero kind (`+0x20a4`) ≠ 0, which covers the Clank and Giant Clank
    sections *(NOTES)*.
  - Ratchet is in a cutscene or scene: `0xa10708` ≠ 0 *(NOTES: 5 during the gold weapon scene)*.
    Confirm the flag for real cutscenes.
  - Ratchet is dying or respawning (state 0x77 *(NOTES)*).
  - On a ship level or the space combat sections (find their `PLANET` values or hero kind).
  - The level is loading, or the pause menu is open.

### 2.3 Player 2 controls

| Input | Action |
|---|---|
| Left stick | Fly, relative to the camera (forward = away from the camera) |
| R2 / L2 | Fly higher / lower within the hover band |
| X | Boost: a short thruster burst (Clank's dash numbers) |
| Square (hold) | **Zap:** lightning beam to the locked target, drains energy |
| Circle | **Dive punch:** dash to the target and punch (Secret Agent Clank style), breaks crates |
| Triangle | With full energy: **Overcharge** (chain lightning). Near Ratchet's back: dock |
| R1 (hold) | **Bolt magnet:** bolts within reach of Clank fly to Ratchet (stretch goal) |
| Select (hold 0.7 s) | Dock |
| Start | Join / undock (pausing stays Player 1's) |

Player 1's controls are unchanged, apart from the tag-team (section 2.5).

### 2.4 Abilities and numbers (initial values, all live-tunable, see section 6)

- **Energy:** 100 max. Regenerates 12/s when not zapping, 40/s while docked. The zap costs
  30/s, the dive punch 10, the boost 15. Overcharge needs 100 and spends it all.
- **Flight:**
  - 7.0 units/s top speed (Ratchet runs 5.7 *(NOTES)*, so Clank can keep up and overtake),
    30 units/s² to speed up, 40 to slow down.
  - Banks into turns (roll up to 0.35 rad by sideways velocity) and pitches forward up to 0.25
    rad with speed.
  - **Boost:** 11.5 units/s for 0.35 s (the Thruster-Pack long jump's speed *(NOTES)*), 0.6 s
    cooldown, flames trail.
- **Hover:** 1.7 above Ratchet's ground height, within 0.6 to 4.0 via R2/L2, eased with a spring.
  Clank never goes below Ratchet's ground height minus 0.5 (no diving through floors under him).
- **Buddy slot:** with the stick idle for 1.5 s, Clank drifts to 1.0 left, 0.6 behind and the
  hover height of Ratchet's shoulder, facing where Ratchet faces. He never just hangs where he
  was left.
- **Leash:**
  - Soft at 7.0 from Ratchet: a pull that grows from 0 at 7 to the full flight speed at 10.
  - Hard at 14.0, or off-screen for 2 s: Clank blinks back to the buddy slot with a gold puff at
    both ends and a short sound.
  - The shared camera stays the game's camera on Ratchet: no split screen.
- **Zap** (Square held):
  - Lock-on: the nearest enemy within 9.0 inside a 35° half-cone around the stick direction (or
    Clank's facing). The lock is sticky while the target stays within 11.
  - Damage ticks every 6 frames, using the Tesla Claw's damage and flags (find them in its fire
    code).
  - Feel target: a common trooper dies after about 1.2 s of zap at the starting value.
  - Blue lightning from Clank's chest to the target (the Tesla Claw's stream, section 3.6), small
    sparks at the target, a looping zap sound while held.
  - With no enemy in reach the beam fires short ahead (0.5 s fizzle, no cost) so it never feels
    dead.
- **Dive punch** (Circle):
  - Dash for 0.22 s at 14 units/s toward the target, or straight ahead.
  - Clank's punch animation on arrival; a hit sphere of radius 1.0 at the fist.
  - Damage: the wrench's × 2, with the wrench's flags `0x10000` *(NOTES)*. Crates break through
    `mods/sweep.py`. Cooldown 0.5 s.
  - A tiny camera kick (0.04 for 6 frames, as the Golden Clank punch).
- **Overcharge** (Triangle at full energy):
  - Wind-up 0.75 s: Clank rises 0.5, spins once and swells to 1.25 size while gold sparks
    gather. This is Golden Clank's `BOMB_DANCE` idea; reuse its spin and wrap code.
  - Then chain lightning: up to 6 targets, the first within 12 of Clank, each next one within 6
    of the last. 3 strong ticks per target over 1.2 s (zap tick × 3 each).
  - A gold burst, camera shake 0.2 for 20 frames, the message "OVERCHARGE!", Ratchet's sound
    definition 24 (the level-up sound *(NOTES)*).
  - **This is a thumbnail shot: make it look great.**

### 2.5 Team moves

- **Shock-Wrench combo:** a target hit by Ratchet's wrench (thrown or swung) and zapped by Clank
  within 1.0 s, in either order, takes double damage for 2 s. A gold burst at the target, a sound,
  and a small "COMBO" flash.
  - Detection: the damage ring at `0xa14c00` *(NOTES)*. Each frame, look at the entries written
    since the last frame (write index `0xa10954`): source = Ratchet's moby and flags & `0x10000`
    → mark the target with the frame number.
- **Two pilots, one Giant Clank** (needs Golden Clank, bought):
  - While Clank is docked, P2 is active and Golden Clank mode is on (P1's L3 + R3, as now),
    **P2's Square, Circle and Triangle drive Giant Clank's punch, missiles and bomb**. P1 keeps
    movement, jump, shockwave and hover.
  - P2 can undock only after P1 switches the mode off. Undocking with the mode on switches it off
    with Golden Clank's normal switch-off (burst and sound).
  - Implementation: a shared word (`COOP_PILOT`, section 3.2). Golden Clank's input code
    (`gc_pad`/`gc_input`, which today takes `MOVES` from every button word of `PAD` and its press
    history) takes them from P2's pad block instead while that word is set. In that case it leaves
    P1's Square, Circle and Triangle out of the game as now, so Ratchet does nothing with them.
    Touch Golden Clank as little as possible: one branch at the place it reads the move buttons,
    and one at the mode switch for the undock rule.

### 2.6 AI Clank ("the Clank Zapper that doesn't suck")

The same body, flight and abilities, driven by a small state machine instead of a pad:

- **Follow:** stay at the buddy slot.
- **Engage:** the nearest enemy within 8 of Ratchet in front of him → zap it at 60% damage.
  Dive punch an enemy within 2.5 of Ratchet ("protect"). Never steal the last hit on a boss.
  Bosses can be told by class once seen; to start with, at most 30% of a boss's damage.
- **Retreat:** below 25 energy, back to the slot until 70.
- **Overcharge** only with 5 or more enemies within 10 of Ratchet.
- **Idle:** Ratchet still for 10 s and no enemies within 15 → dock until something happens.

### 2.7 HUD

- A **P2 badge** while Clank is out: a small Clank icon (find his icon id among the HUD icons,
  `ICON_SPRITE`/`ICON_DRAW`, see `mods/chargeboots/menu.py`), the text "P2" and an energy bar
  (`FILL_RECT` `0xCA72C`, as the Weapon levels' bar in `mods/weaponlevels/display.py`).
  - Gold `0x8029B4F0`-ish when full, the game's slider colours otherwise.
  - Place it top-left under the game's own widgets, checked on several levels with screenshots,
    and drawn at the HUD hook.
- Messages: "PLAYER 2 JOINED", "CLANK DOCKED", "OVERCHARGE!". Through `SHOW_MESSAGE` with own text
  entries, as the Weapon levels and Golden Clank do.
  - Their visibility depends on the HelpDesk text option.
  - Because the video depends on them, prefer drawing these three with the game's text drawing
    on the HUD hook, so they show regardless of the option. Find the function the HUD uses for its
    counters (the Weapon levels found the ammunition count's draw `0xd4838`, which writes with a
    format).

### 2.8 Sounds

Use the game's own: the pop-off (Ratchet's definition 24 + 1, the Golden Clank switch sound
*(NOTES)*), the zap loop (the Tesla Claw's sound definition), the dive punch (the wrench's swing
sound), the dock clack, the blink-back (a short sound of the Thruster-Pack), the overcharge
(definition 24). If Clank's walking model keeps its own sound definitions, strip them as
`giant_model()` does, or load his level's bank cut down as `giant_sounds()` does.

---

## 3. Technical design

### 3.1 Controller 2 (the key finding, *static*, verify first)

The game already reads every controller port; it just stops at the first connected one:

- `0x11e2d4` (called from `0x12284`, `0x1313c`, `0xe14a0`, `0xe14bc`, `0xe14f8`, `0xe1528`)
  loops `r28` = port 0..3. For each port:
  - `r30` = `0x965540 + port * 0x564`, the port's pad block, laid out as `PAD`.
  - It calls the pad driver's virtual function `vtable + 0x10` with (r3 = `*(0x902edc)`,
    r4 = port, r5 = the block). The driver is `0x4ec160`: `cellPadGetInfo2`, then
    `cellPadGetData(port, …)`. It sets block `+0x9c` and `+0x458` to 1 when the port delivered
    data, and 0 when not.
  - If block `+0x9c` ≠ 0 it **copies the whole block (0x564 bytes) to `PAD` (`0x964a40`)** and
    returns.
- So with Player 1 on port 0, ports 1–3 are never read. `cellPadGetData`'s stub is `0x64f9a4`
  (NID `0x8b72cda1`, slot `0x701bcc`); `cellPadGetInfo2` is `0x64f9c4`.
- **The mod:** hook the function's epilogue at **`0x11e3a0`** (`ld r0, 0xa0(r1)`, word
  `0xE80100A0`), a plain hook whose routine does that instruction and returns.
  - In it: if port 0's block (`0x965540 + 0x9c`) is active, call the same virtual function for
    **port 1 with the block `0x965AA4`**. Copy the call sequence at `0x11e300..0x11e334`, saving
    and restoring r2.
  - Then compute this frame's "pressed" bits for P2 from its held bits and the previous frame, if
    the block's own press words aren't filled the same way as the game's. Check live whether
    `+0xa4` in the port block is already "pressed this frame".
  - Result: **P2's pad is `0x965AA4`, in exactly `PAD`'s layout**: sticks at +0x8/+0xc, held
    buttons at +0xa0, pressed at +0xa4, and so on *(NOTES for `PAD`)*.
- **Edge case:** if Player 1's controller sits on port 1 (RPCS3 with Player 1 unbound), the game
  takes port 1 as P1. Then read nothing for P2 (P2 is "the next active port after P1's"). Keep the
  rule "P2 = the first active port after the one the game took", and test it.
- Check how often `0x11e2d4` runs per frame (6 call sites). Read P2 once per game frame, not per
  call: keep the last frame number (`FRAME_COUNTER`).
- **RPCS3:** Pads → Player 2 must have a handler and a device. Before touching
  `~/.config/rpcs3/input_configs/global/Default.yml` (or the game's custom config), back it up and
  **ask the user**. For tests without a second person, see section 5 (a second virtual pad).

**Spike, step 0** (do this before anything else, half a day):
1. Build a mod that only hooks `0x11e3a0` and reads port 1.
2. Bind a second (virtual) pad as RPCS3's Player 2.
3. With `tools/peek.py` read `965aa4` +0x9c / +0xa0 / +0x8 while pressing on pad 2.
4. Write the finding into `NOTES.md` (new section *Co-op*).

If port 1 never becomes active, find out why (`cellPadGetInfo2`'s port status; RPCS3's settings)
before going on. The fallback is AI-only, which is still a video.

### 3.2 Memory

- **Shared words** (for Golden Clank): the state block is full. Golden Clank uses
  `+0x2a0..+0x340` and `STATE_END` = `STATE + 0x340`. Extend `STATE_END` in `game.py` by 0x40 and
  document in its comment block:
  - `+0x340 COOP_OUT`: 0 docked, 1 Clank flying.
  - `+0x344 COOP_P2`: P2 active.
  - `+0x348 COOP_PILOT`: P2 drives Giant Clank's arms.
  - `+0x34c` the address of P2's pad block in use (0 = none).
  - The rest is spare.
  - Check `build.py` (`STATE_END` becomes the RW segment's new memsz; the data segments start at
    `0x1610000`, far above) and that `patch.py` takes it from the patch files as built.
- **The mod's own block:** writable data in segment `rw` (as Golden Clank's `GIANT`), so every
  tuning value and the runtime state can be read and written live with `tools/peek.py`. Lay it out
  in the module docstring:
  - **Runtime:** mode, Clank's position, velocity, euler and hover height; the mobys (body,
    wings, two jets, pack hidden flag); energy, timers (boost, punch, overcharge, leash
    off-screen, docking), the lock-on target, the combo marks (16 entries {moby, frame}), the AI
    state, the frame P2 was last read.
  - **Tuning:** section 6.
  - Put it at a fixed offset from a label the tools can find, as `scratchpad g.py` finds
    `GIANT` "from the texts" *(NOTES)*: give `tools/` a helper that prints the block's address.

### 3.3 Clank's body

- **The model:**
  - Free Clank is class `0x57` (73 bones, 19 animations), and exists only in levels 6 and 10
    *(NOTES)*. Install it in every level as Giant Clank's model is (Golden Clank: model and
    textures embedded from the player's RC1 data, installed once per boot, model fix-up
    `0xDBC38`, mesh groups pointed at own texture entries).
  - Generalise `rc2data._giant(rc1, cls)` to `_model(rc1, level, cls)`. It reads level 18 only
    today. Take level 6 for class `0x57`, and keep `giant_*` as thin wrappers so Golden Clank's
    output is byte-for-byte unchanged (check the exported `goldenclank` patch file doesn't change).
  - Watch the heaps: about 53 MB of the main heap were free on the Gemlik Base *(NOTES)*. Measure
    the model's size and log it.
- **The moby:**
  - `SPAWN(0x259)` (backpack Clank's class, in every level, no update of its own), then:
    - `+0x24` = the installed model
    - `+0x30` = 0xff (update at any distance)
    - `+0x31` = 1
    - `+0x32` = `0x2000` (draw distance; 0 = never drawn)
    - clear `+0x34` bit 0x2 (else the moby loop skips it: no animation, no bounds, never drawn)
  - The moby loop then animates it and keeps its bounds *(NOTES)*. Set the place `+0x10`, the
    euler `+0x40`, the scale `+0x2c` every frame.
  - `SPAWN` returns 0 when no moby is free: then try again next frame and stay docked.
- **Animations** of class `0x57`, traced in his own levels *(NOTES)*: idle 0, fidget 1, walk 2→3,
  fall 4, hurt 6, jump 7, ledge climb 11, punch 15. Confirm on the installed model, then use:
  - flying: the fall animation 4 held or slowed
  - boost: 4 with the pitch
  - zap: an arm-forward frame (look through his 19)
  - dive punch: 15
  - pop-off: jump 7
  - docking: fall 4 → the seat
  Use `MOBY_SET_ANIM` `0xFDDC0` (moby, animation, 0, blend frames).
- **Wings and jets:**
  - Clank's dash already puts the Thruster-Pack's device (class `0x260`, animation 1 = wings out,
    offset `CLANK_WINGS_OFFSET` (0.174, 0, 0.359)) on Clank and drives its two jets (`JET_SPAWN`
    `0x2AA928`, `JET_EMIT`, draw callback via `DRAW_REGISTER`) *(NOTES / clank.py)*.
  - Reuse that: a device moby placed from free Clank's back joint every frame (joint matrix
    `0xf1038`), wings out.
  - The jets' draw callback insists on a device of class `0x260` *(NOTES)*: fine, that's what he
    carries. Flames under the jets while flying: Golden Clank's hover flames (`FIRE` `0x12e3e8`,
    `SPARK` `0x1268f8`, its numbers in `FLAMES`/`FIRE_LOOK`), smaller.
- **Backpack Clank and the pack on Ratchet while Clank is out:**
  - Hide them. Scale 0 on their `+0x2c` every frame, or a joint manipulator with weight 1 and
    scale 0 on bone 1, which hides all of backpack Clank *(NOTES)*. Restore them on docking.
  - Golden Clank also sets backpack Clank's scale and seat every frame (`gc_clank_seat`). While
    `COOP_OUT` is set it must leave them alone. That is the second small change in Golden Clank:
    one test of the shared word.
- **The gold:** if Golden Clank is bought, flying Clank is gold too. The colour goes on at the HUD
  hook, from Ratchet's light × `GOLD_TINT` *(NOTES)*.

### 3.4 Flight (per frame, at the frame hook, before the hero)

1. Read P2's stick and buttons (or the AI's virtual stick and buttons).
2. **Camera-relative wish direction:** from `CAMERA_STATE` (`0x9513C0`) +0x350's rows
   (view / left / up) *(NOTES)*. Flatten the view row to the ground plane, so stick-forward is
   "away from the camera".
3. **Velocity:** approach wish × `FLY_SPEED` with `FLY_ACCEL`/`FLY_DECEL` (`APPROACH` `0x109AF0`
   per axis, or own code). Add the boost; add the leash pull.
4. **Height:**
   - The target is Ratchet's ground height + the hover offset. Use Ratchet's z when he's on the
     ground, and his last ground z while he's in the air, so Clank doesn't bob with his jumps.
     `+0x2d8` is "ground below" and can be far below or 0 over drops *(NOTES: the camera bug)*:
     use it only when `+0x418` says he's down.
   - Spring toward the target with `SPRING_STEP` `0x109A68`. Clamp to the floor rule (section 2.4).
5. **Walls:** v1 flies through geometry (a ghost), and the leash plus buddy slot keep him out of
   walls when idle.
   - Stretch goal: a probe ray. `WALL_PROBE` `0x88208` is the hero's own; look for the
     projectile collision the Blaster's shots use (they stop at walls) and use it for Clank's
     segment from last to this frame. If it hits, slide along the wall.
6. **Place and turn:** position += velocity / 60.
   - Yaw toward the velocity, or the lock-on target while zapping.
   - Roll by sideways velocity, pitch by speed.
   - Wrap the euler.
7. **Leash:** distance to Ratchet; off-screen from the camera's view row and a cone (dot < 0.5 and
   distance > 4), counted in frames; the blink-back.

### 3.5 Docking, joining and the pop-off

All three are short scripted movements on Clank's own position, from or to backpack Clank's
seat. Get the seat from backpack Clank's moby `+0x10` and its matrix rows at `+0xc0` *(NOTES)*:

- **Pop-off:** over 30 frames from the seat along an arc (up 1.2, back 0.8 in Ratchet's frame),
  then free.
- **Dock:** over 15 frames to the seat, easing in, then hide free Clank and show backpack Clank.
- Puffs at the seat on both, sound, message.

### 3.6 Combat

- **Targets:** `COLLECT` (`0x5E598`; centre, radius, flags, ignore moby, damage descriptor →
  count, pointers at `0xa14a00`) *(NOTES)* around Clank.
  - Keep the enemies. Leave out crates (`IS_CRATE` `0x10AF88`), bolts, Ratchet and his own mobys.
  - Find a reliable "is an enemy that can be hit" test: the damage slot `+0xa4` (0xff = none) and
    the per-class data are candidates. Watch what `COLLECT`'s flags select (Box Breaker's call
    takes crates; the hyper-strike's takes enemies).
- **Damage:** `DEAL_DAMAGE` `0x105C08` (target, source = Clank's moby, flags, damage, position,
  direction) *(NOTES)*.
  - **Source = Clank's moby, not Ratchet's.** Check `mods/weaponlevels/experience.py`: kills must
    not count for the weapon in Ratchet's hand (proposal, see the open questions).
  - Bolts drop as usual.
- **The lightning:** the Tesla Claw is class `0xb1`. Its stream `0x2b4818` and draw `0x2b8520`
  drew blue lightning when reused by accident *(NOTES, Golden Clank's hover flames)*.
  - Reverse how the Tesla Claw's moby drives them (its variables: from, to, target, life).
  - Drive the same draw from Clank's chest joint to the target every frame of the zap.
  - For the overcharge: one stream per chain link.
  - If it can't be driven freely: a trail (`TRAIL` `0x1349F0`) of sparks along a jittered
    polyline is the fallback. Make it look like lightning (bright core, short life, a new random
    offset every 2 frames).
- **Dive punch hit:** a sphere at Clank's fist on the punch's hit frames. Crates via
  `mods/sweep.py` (`USES = (sweep,)`). The wrench damage and flags as Box Breaker uses them.

### 3.7 Gating Ratchet's pack moves (optional, see the open questions)

If the pack goes with Clank, Ratchet can't glide, hover or long/high-jump while Clank is out.
The affected states are 8, 0xa, 0xd, 0xe, 0xf and 0x10 (the glide test `0xc4f0c`, the crouch
chooser `0xa56d8`) *(NOTES)*.

- Golden Clank already hooks set_state at `0xb72dc` as a **jump** hook (`NO_FLIPS_HOOK`) and the
  double jump at `0xc4e64`. Don't hook those again.
- Either make `0xb72dc` a shared chained site in `game.py` (both mods: turn the unwanted states
  into 7), or block at the choosers.
- A short help message the first time: "Clank has your Heli-Pack!"

### 3.8 Hooks (summary)

| Site | Kind | Routine | What |
|---|---|---|---|
| `0x11e3a0` | plain (word `0xE80100A0`) | `coop_pad` | read port 1 into `0x965AA4` |
| `FRAME_HOOKS` | chain | `coop_frame` | modes, AI, flight, combat, team moves |
| `HUD_HOOK` | chain | `coop_hud` | late placement (wings, jets, flames, beams), gold colour, HUD badge and messages |
| `0xb72dc` or the choosers | see 3.7 | `coop_pack` | optional pack gating |
| none new in Golden Clank | — | — | two tests of shared words (2.5, 3.3) |

Model install: as Golden Clank does it, once per boot and again per level where needed. Copy
its structure, not its code paths.

### 3.9 Robustness

- **Level load:** all mobys are gone. Detect it (`PLANET` change, or `FRAME_COUNTER` going back to
  a small number) and clear every moby pointer in the block before using it. Clank starts docked
  in the new level.
- **Death and respawn:** dock at once (no animation), clear manipulators and effects the mod put on
  any moby, reset energy.
- **Pause menu:** no input to Clank, nothing moves (the frame hooks may not run, so check).
- **Clank sections and Giant Clank sections:** suspended (2.2).
- **Moby budget:** body, device, 2 jets and short-lived effects. Never spawn per frame without
  deleting. Log the count of live mobys once per second in the trace while testing.
- **NaN safety:** the stick at rest can give 0/0 in normalisations, so guard every division.

---

## 4. Plan

Each phase ends with something **seen by you in game** (screenshot or a 60 fps clip through
`tools/stage.py rec`, read back frame by frame), a commit, and a `NOTES.md` entry. The bold
checkpoints need the user.

| Phase | Goal | Done when |
|---|---|---|
| **0 Spike** | Controller 2 readable (3.1) | `965aa4` +0xa0 changes with pad 2's buttons; +0x8/+0xc with its stick. **The user's real second pad works as P2.** |
| **1 Out of the pack** | Clank's model in every level; join / dock with pop-off; backpack hidden; Clank idles at the buddy slot | on Novalis and Gemlik: join, 30 s, dock, 5 times each, no crash; clip of the pop-off |
| **2 Flight** | 3.4 complete incl. boost, leash, blink-back, banking, wings and flames | flown around 3 levels for 2 min each; never lost; **the user flies it and confirms speed and feel** |
| **3 Zap + punch** | lock-on, beam, damage, energy, dive punch, crates | a trooper dies in about 1.2 s of zap; crates break; the beam looks like lightning in a 60 fps clip; **user: "feels good"** |
| **4 Showpieces** | Overcharge; two pilots, one Giant Clank | overcharge hits 6 enemies in a clip; the tag-team works with P1 driving and P2 punching; **the user plays it with someone** |
| **5 Combo + AI + menu** | Shock-Wrench combo; AI Clank; the "Clank Zapper" menu item and its save byte | AI clears an easy fight alone without getting lost; the menu item saves and loads |
| **6 HUD, sounds, polish** | badge, bar, three messages, all sounds, the gold | screenshots on 4 levels; sounds heard by the user |
| **7 Hardening** | 3.9 on all 19 levels (`tools/stage.py travel`) | per level: travel, join, fly 10 s, zap, dock; plus death, respawn, level change and pause with Clank out; no crash |
| **8 Release** | `build.py --export` → `patches/coop-npea00385.bbpatch`; README row and section "Co-op" (controls, RPCS3 Player 2, Parsec for online); `patch.py --list` shows it | the user patches a clean EBOOT with `patch.py` and plays |

Pack gating (3.7) and the bolt magnet go in when the user wants them, after phase 4.

---

## 5. Tools to add or extend

- **`tools/vpad.py`:** options `--name` and `--fifo`, so a second virtual pad ("Backport P2") can
  run beside the first. RPCS3's Player 2 is bound to it (with the user's consent, backup of the
  config).
- **`tools/ingame.py --p2`:** start the P2 pad before RPCS3, as it does for P1's.
- **`tools/coop.py`** (new): scripted P2 input for tests and filming:
  - `join`, `dock`, `fly X Y SECONDS`, `zap SECONDS`, `punch`, `overcharge`, `goto-slot`
  - `state`: prints the mod block (mode, energy, position, target, mobys) via `tools/live.py`
  - `block`: prints the block's address
- **`tools/stage.py`:** commands `p2 join|dock`, `energy full`, `enemies` (list the enemy mobys
  near Ratchet with their health, for staging fights), and spots for the video (section 7).
- **`tools/trace.py`:** optional co-op columns (energy, mode, target, live moby count) behind an
  environment switch.

---

## 6. Tuning values (the writable block; names for the module)

| Name | Start | Unit / meaning |
|---|---|---|
| `FLY_SPEED`, `FLY_ACCEL`, `FLY_DECEL` | 7.0, 30.0, 40.0 | units/s, units/s² |
| `BOOST_SPEED`, `BOOST_TIME`, `BOOST_COOLDOWN` | 11.5, 0.35, 0.6 | units/s, s, s |
| `HOVER`, `HOVER_MIN`, `HOVER_MAX`, `HOVER_RATE` | 1.7, 0.6, 4.0, 2.0 | units, units, units, units/s for R2/L2 |
| `HOVER_SPRING` | 12.0, 0.8, 9.0 | stiffness, damping, max speed (`SPRING_STEP`) |
| `SLOT` | (-0.6, 1.0, 1.7) | behind, left, up from Ratchet |
| `SLOT_IDLE` | 1.5 | s of idle stick before drifting to the slot |
| `LEASH_SOFT`, `LEASH_FULL`, `LEASH_HARD`, `OFFSCREEN` | 7.0, 10.0, 14.0, 2.0 | units, units, units, s |
| `ENERGY_MAX`, `REGEN`, `REGEN_DOCKED` | 100, 12, 40 | /s |
| `COST_ZAP`, `COST_PUNCH`, `COST_BOOST` | 30, 10, 15 | /s, each, each |
| `ZAP_RANGE`, `ZAP_KEEP`, `ZAP_CONE`, `ZAP_TICK`, `ZAP_DAMAGE` | 9.0, 11.0, 35°, 6, Tesla × 0.6 | units, units, half-angle, frames, damage |
| `PUNCH_DASH`, `PUNCH_TIME`, `PUNCH_RADIUS`, `PUNCH_DAMAGE`, `PUNCH_COOLDOWN` | 14.0, 0.22, 1.0, wrench × 2, 0.5 | |
| `OVER_WINDUP`, `OVER_TARGETS`, `OVER_FIRST`, `OVER_LINK`, `OVER_TICKS` | 0.75, 6, 12.0, 6.0, 3 | s, count, units, units, ticks of zap × 3 |
| `COMBO_WINDOW`, `COMBO_TIME`, `COMBO_FACTOR` | 60, 120, 2.0 | frames, frames, × |
| `POP_ARC`, `POP_FRAMES`, `DOCK_FRAMES`, `DOCK_HOLD` | (1.2, 0.8), 30, 15, 0.7 | units, frames, frames, s |
| `AI_ENGAGE`, `AI_PROTECT`, `AI_DAMAGE`, `AI_RETREAT`, `AI_IDLE` | 8.0, 2.5, 0.6, (25, 70), 10 | units, units, ×, energy, s |
| `HUD_BADGE` | (x, y, w, h) | placed with screenshots |

---

## 7. The video (what the build must make possible)

**Title** (pick with the user): *"I Added 2-Player Co-op to Ratchet & Clank 1 (Player 2 is
Clank)"*. Alternative: *"After 24 Years, Clank Can Finally Fight"*.

**Thumbnail** (the `backport-brand` skill):
- Real frame: Ratchet and flying Clank side by side, Clank zapping a robot.
- A gold ring around Clank, the gold plate `P2`, the headline `FINALLY.`, the tag `R&C · 2002`.

**Shots to stage** (`tools/stage.py` spots; all 60 fps, game sound):

| # | Shot | Needs |
|---|---|---|
| 1 | Cold open (≤ 5 s): mid-fight, "PLAYER 2 JOINED", pop-off, first zap kills a robot | phases 1–3, a staged group of enemies |
| 2 | "24 years a backpack": Clank folded on Ratchet's back, slow push-in | the stock game |
| 3 | The comment "Imagine if this was the Clank Zapper instead" on screen | the edit |
| 4 | Build beats with bloopers: Clank inside a wall, the first zap fizzling, the first kill | keep failing clips as you develop them! |
| 5 | Co-op fight with the second player (ideally a guest; online via Parsec is a story beat) | phase 3 |
| 6 | Shock-Wrench combo in slow motion | phase 5 |
| 7 | Overcharge clearing a room | phase 4 |
| 8 | Two pilots, one Giant Clank (the climax) | phase 4, Golden Clank bought |
| 9 | (optional) "Clank has your Heli-Pack!": the co-op platforming beat | 3.7 |
| 10 | Download + "next: Hard Mode" + 6 s end screen | release |

**Shorts:** the pop-off (15 s), overcharge (20 s), two pilots (30 s), the wall blooper (10 s).
Edit everything with the `backport-brand` editor (`edit.py`): stingers per chapter, gold tags
naming the moves ("+ ZAP", "+ OVERCHARGE"), 6 s end screen.

---

## 8. Definition of done

- Every phase's "done when" met; the bold checkpoints confirmed by the user.
- Built alone and with every other mod (`build.py --mods coop`, and all): both run.
- `patches/coop-npea00385.bbpatch` exported; `README.md` and `NOTES.md` updated; no game data
  added to the repository.
- The Golden Clank patch file is unchanged when the co-op mod isn't built in, apart from the two
  shared-word tests. Re-export it and compare.

## 9. Open questions for the user (ask before the phase that needs them)

1. **The pack goes with Clank?** Ratchet can't glide or long-jump while Clank is out (3.7):
   more co-op, but less freedom solo. Suggestion: yes in co-op, never in AI mode.
2. **Kills by Clank and the Weapon levels:** suggestion: they don't count for Ratchet's weapon.
3. **AI Clank default:** off (suggestion), so the game stays the game until chosen.
4. **Lightning colour:** the Tesla Claw's blue (suggestion), or gold to match Golden Clank. Gold
   would only be used when Golden Clank is bought.
5. **The second player for the video:** a friend, a viewer from Discord, or More Xem (streamed the
   Charge Boots). A collab doubles the reach.
