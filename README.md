# Box Breaker, Charge Boots, strafing and a thruster dash for Ratchet & Clank HD

Mods for the first Ratchet & Clank in its PS3 HD version (**NPEA00385**, the European release,
also the first game on the European Trilogy disc). Most of them bring over mechanics from
Ratchet & Clank 2.

| Mod | What it does | Controls |
|---|---|---|
| Box Breaker | The hyper-strike breaks every crate within 14 units, with RC2's screen shake; the bolts fly to Ratchet. | Jump, then Square |
| Charge Boots | RC2's charge dash, with its animation, sounds and boots model. An item of its own under Foot Items on the pause menu's Gadgets page, on by default. | Tap R1 twice and hold it |
| Bolt crank boost | Turns a bolt crank at the speed of a charge. | Tap R1 twice and hold it at a crank |
| Strafing | RC2's strafing, backwards walk and side flips, and RC2's quicker speeding up and slowing down. | Hold L2 or R2 |
| Clank's thruster dash | Clank makes Ratchet's Thruster-Pack long jump: wings and jets out, lying flat, breaking crates, bouncing off walls. | As Clank: hold R1, push the stick, press X |
| Weapon levels | Weapons collect experience from the enemies they kill and reach a second level once: the game's own gold version where there is one, three rockets a shot for the R.Y.N.O., twice the damage for the Visibomb Gun, Walloper and Drone Device. The Taunter collects what the enemies it lured are worth; at level 2 a lured enemy that reaches Ratchet stands stunned until it is hit or a few seconds pass. A bar in the weapon display shows the experience; a level-up fills the weapon up and comes with a message, a flash, a burst of gold and rising gold smoke from the weapon; level 2 weapons are gold in Ratchet's hand, have a gold icon and a "Gold" name, and draw bolts in. | Kill enemies with the weapon in hand |

Everything was made and tested on RPCS3 under Linux. It has not been tried on a console.

## Patching the game

You need Python 3 and the game's **decrypted** executable.

1. In RPCS3 choose *Utilities > Decrypt PS3 Binaries* and pick the game's
   `dev_hdd0/game/NPEA00385/USRDIR/EBOOT.BIN`. RPCS3 writes `EBOOT.elf` next to it.
   (With the Trilogy disc, `PS3_GAME/USRDIR/RC1.ppu.self` decrypts to the same file.)
2. Run the patcher and answer its three questions:

   ```
   python patch.py
   ```

   It lists the executables it finds in RPCS3's game folder and in the current folder, says
   which of them can be patched, and asks which one to use; you can also type or drag in the
   path of another file. Then it asks which mods you want (all of them when you just press
   Enter) and where the result should go. The first choice there writes `EBOOT.BIN` in the
   same folder, which is the file RPCS3 boots, and keeps the file that was there as
   `EBOOT.BIN.bak`.
3. Close RPCS3 completely and start the game again.

Without questions: `python patch.py EBOOT.elf -o EBOOT.BIN`, or `--replace` to put the
result in the file's own place (the file is kept as `<file>.bak`). That puts in every mod;
`--mods boxbreaker,strafing` picks some, and `python patch.py --list` shows their names.

Every mod is a patch file of its own in `patches/`, and any of them can be combined. To
change your choice later, run the patcher again on the patched file: it recognises its own
mods, takes them out and puts in the ones you pick now.

The patcher only accepts the one executable it was made for (it compares checksums), so a
wrong file, or one modified by something else, is refused instead of broken.

**To undo it**, copy `EBOOT.BIN.bak` back over `EBOOT.BIN`.

## What is in here

- `patch.py`: the patcher. Plain Python, no packages needed.
- `patches/`: one patch file per mod (`boxbreaker`, `chargeboots`, `strafing`, `clank`,
  `weaponlevels`); the bolt crank boost is part of the Charge Boots.
- `mods/`: the source of the mods, one file each, with what the mod does and where its numbers
  come from at the top. `game.py` holds what they share (the game's functions and addresses,
  the memory they use), `sweep.py` the crate sweep three of them call.
- `build.py`: assembles the mods, embeds the data in `assets/` and writes the patched
  executable and the patch files.
- `assets/`: data taken from Ratchet & Clank 2 that the mods embed: two of Ratchet's
  animations, the two charge sounds, and the Charge Boots model with its texture and menu
  icons. The patch files contain the same data.
- `tools/`: what the mods were found and tested with (disassembly, cross references, a
  reader for the game's archives, a tracer that reads a running RPCS3's memory).

## Building from source

Only needed to change the mods. It takes the packages in `requirements.txt` (capstone and
keystone) and the same decrypted executable:

```
python -m venv .venv
.venv/bin/pip install -r requirements.txt
RC1_ELF=/path/to/EBOOT.elf .venv/bin/python build.py --export
```

That writes `build/EBOOT.elf` with all mods and, with `--export`, every mod's patch file to
`patches/`. `build.py --help` lists `--mods` (which mods go into the executable), the mods'
tuning options (Box Breaker radius, charge speeds) and `--install`, which copies the result
into RPCS3's game folder. Instead of the environment variable, the path can be put in a file
`rc1_elf.path` next to `build.py`.

A new mod is a new file in `mods/`, added to the list in `mods/__init__.py`, which also says
what such a file has to contain. Mods do not call each other; where two of them need the same
game instruction, `build.py` and the patcher chain them.

## Limits

- Only this executable is supported. Other regions and versions of the game have their code
  at other addresses.
- The patch files are built with the default tuning; other values (radius, speeds) need a
  build from source.
- Clank's dash was tuned and play-tested on his two sections only as far as the author played
  them; a dash off a ledge keeps flying for up to 2.5 seconds before he falls.
- Clank does not rise higher while X is held, as Ratchet does in his long jump.
- Weapon levels: a kill counts for the weapon in Ratchet's hand at that moment, whatever
  caused it. The experience is kept in the save file in places the game does not use; a save
  made with the mod loads without it and the other way round.

## Licence

The code in this repository (the patcher, `build.py`, `mods/` and the tools) is under the Apache
License 2.0, see `LICENSE`. That does not cover the game data: the files in `assets/` and the
data embedded in the patch files come from Ratchet & Clank 2 and belong to its owners.
