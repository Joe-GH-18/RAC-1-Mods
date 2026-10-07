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

Everything was made and tested on RPCS3 under Linux. It has not been tried on a console.

## Patching the game

You need Python 3 and the game's **decrypted** executable.

1. In RPCS3 choose *Utilities > Decrypt PS3 Binaries* and pick the game's
   `dev_hdd0/game/NPEA00385/USRDIR/EBOOT.BIN`. RPCS3 writes `EBOOT.elf` next to it.
   (With the Trilogy disc, `PS3_GAME/USRDIR/RC1.ppu.self` decrypts to the same file.)
2. Run the patcher and answer its two questions:

   ```
   python patch.py
   ```

   It lists the executables it finds in RPCS3's game folder and in the current folder, says
   which of them can be patched, and asks which one to use; you can also type or drag in the
   path of another file. Then it asks where the result should go. The first choice writes
   `EBOOT.BIN` in the same folder, which is the file RPCS3 boots, and keeps the file that was
   there as `EBOOT.BIN.bak`.
3. Close RPCS3 completely and start the game again.

Without questions: `python patch.py EBOOT.elf -o EBOOT.BIN`, or `--replace` to put the
result in the file's own place (the original is kept as `<file>.bak`).

The patcher only accepts the one executable it was made for (it compares checksums) and
checks the result the same way, so a wrong or already modified file is refused instead of
broken.

**To undo it**, copy `EBOOT.BIN.bak` back over `EBOOT.BIN`.

## What is in here

- `patch.py`: the patcher. Plain Python, no packages needed.
- `patches/boxbreaker-npea00385.bbpatch`: the changes it applies, with all mods switched on.
- `build.py`: the source of the mods. It assembles the new code, embeds the data in `assets/`
  and writes the patched executable and the patch file.
- `assets/`: data taken from Ratchet & Clank 2 that the mods embed: two of Ratchet's
  animations, the two charge sounds, and the Charge Boots model with its texture and menu
  icons. The patch file contains the same data.
- `tools/`: what the mods were found and tested with (disassembly, cross references, a
  reader for the game's archives, a tracer that reads a running RPCS3's memory).

## Building from source

Only needed to change the mods. It takes the packages in `requirements.txt` (capstone and
keystone) and the same decrypted executable:

```
python -m venv .venv
.venv/bin/pip install -r requirements.txt
RC1_ELF=/path/to/EBOOT.elf .venv/bin/python build.py --export patches/boxbreaker-npea00385.bbpatch
```

`build.py --help` lists the tuning options (Box Breaker radius, charge speeds, building
without the Charge Boots) and `--install`, which copies the result into RPCS3's game folder.
Instead of the environment variable, the path can be put in a file `rc1_elf.path` next to
`build.py`. The top of `build.py` describes each mod and where its numbers come from.

## Limits

- Only this executable is supported. Other regions and versions of the game have their code
  at other addresses.
- The mods are always all on in the patch file. `build.py` can leave out the Charge Boots;
  the others have no switch yet.
- Clank's dash was tuned and play-tested on his two sections only as far as the author played
  them; a dash off a ledge keeps flying for up to 2.5 seconds before he falls.
- Clank does not rise higher while X is held, as Ratchet does in his long jump.

## Licence

The code in this repository (the patcher, `build.py` and the tools) is under the Apache
License 2.0, see `LICENSE`. That does not cover the game data: the files in `assets/` and the
data embedded in the patch file come from Ratchet & Clank 2 and belong to its owners.
