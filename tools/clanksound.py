#!/usr/bin/env python3
"""clanksound.py: pick the co-op Clank's move sounds from every sound of the game.

  .venv/bin/python tools/clanksound.py              the browser (run it in a terminal of its own)
  .venv/bin/python tools/clanksound.py list [all|here|every]   the sounds as text
  .venv/bin/python tools/clanksound.py play ID      play a sound on this computer
  .venv/bin/python tools/clanksound.py give MOVE ID [VOLUME]   give it to a move and save

Every level has a sound bank of its own (level<N>/sound.bnk) and the same sound sits at another
index in each. A sound here is known by its ID, a hash of its grains and samples
(bank2wav.Bank.fingerprint), so a pick plays on every level that has it; the ones in all 19
banks (the hero's, the weapons', the gadgets') are safe everywhere. Its owner is the class whose
model lists it (the level's engine.ps3 +0x48 table).

The picks go to mods/coop/sounds.json (a move: label, volume, its index per level), which the
build reads (mods/coop/layout.py); in a game started under tools/trace.py with that build they
are also written into the mod's block at once, so the next zap already plays the new one. A pick
some levels lack plays everywhere once built: the build cuts it out of a level that has it into a
bank of the mod's own (layout.OWN_BANKS); live it plays only where the level's bank has it.
Moves: zap, ram, pound, join, dock, blink (layout.SOUND_MOVES). The catalogue and the rendered
sounds are kept in build/sounds/.
"""
import curses
import hashlib
import json
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

from bank2wav import RATE, Bank, write_wav    # noqa: E402
from mods.coop import layout as L             # noqa: E402
from mods.rc2 import source                   # noqa: E402

CACHE = os.path.join(ROOT, "build", "sounds")
CATALOG = os.path.join(CACHE, "catalog.json")
PLANET = 0x969C70                             # mods/game.py: the level loaded
LEVELS = ["Veldin", "Novalis", "Aridia", "Kerwan", "Eudora", "Rilgar", "Blarg Station", "Umbris",
          "Batalia", "Gaspar", "Orxon", "Pokitaru", "Hoven", "Gemlik Base", "Oltanis", "Quartu",
          "Kalebo III", "Drek's Fleet", "Veldin (2)"]    # (tools/stage.py)
OWNERS = {0x0: "Ratchet", 0x57: "Clank", 0xB1: "Tesla Claw", 0xC3: "Charge Boots' boots", 0xCB: "Decoy Glove",
          0x1A3: "Giant Clank", 0x1DF: "Drone Device", 0x259: "backpack Clank", 0x260: "Thruster-Pack",
          0x593: "Giant Clank's shock", 0x5F3: "Giant Clank's bomb"}   # the classes the mods know by name
MOVES = [move for move, _ in L.SOUND_MOVES]
FILTERS = ("all 19 levels", "this level", "every sound")


# The catalogue ---------------------------------------------------------------------------------

def owners_by_index(engine):
    """The level's bank index -> the classes whose models list it (engine.ps3 +0x48)."""
    table = struct.unpack_from(">I", engine, 0)[0]
    count = struct.unpack_from(">I", engine, table)[0]
    remap = struct.unpack_from(">I", engine, 0x48)[0]
    out = {}
    for i in range(count):
        cls = struct.unpack_from(">I", engine, table + 4 + 8 * i)[0]
        off, n = struct.unpack_from(">HH", engine, remap + 8 + 4 * i)
        for k in range(n):
            out.setdefault(struct.unpack_from(">I", engine, remap + off + 4 * k)[0], set()).add(cls)
    return out


def length(bank, index):
    """Seconds the sound lasts (its tones' starts and lengths; 28 samples per 16 bytes)."""
    end, ticks = 0.0, 0
    for kind, data, wait in bank.grain_list(index):
        if kind == 1:
            sample, volume, note, fine = bank.tone(data)
            rate = 48000 * 2 ** ((60 - (-note + fine / 128)) / 12) if note < 0 else 44100 * 2 ** ((60 - (note + fine / 128)) / 12)
            end = max(end, ticks / 240 + len(sample) // 16 * 28 / rate)
        ticks += wait
    return round(min(end, 8.0), 2)


def build_catalog():
    """{ID: its levels {level: first index}, owner classes, length}, and under "at" every
    "level/index" -> ID (a bank can hold the same sound twice)."""
    rc1 = source("rc1")
    sounds, at = {}, {}
    for level in range(L.LEVEL_COUNT):
        print(f"\rreading the banks: {LEVELS[level]:<16}", end="", flush=True)
        bank = Bank(rc1.read(f"level{level}/sound.bnk"))
        owners = owners_by_index(rc1.read(f"level{level}/engine.ps3"))
        for index in range(bank.count):
            if not bank.grain_list(index):
                continue
            sid = hashlib.sha1(bank.fingerprint(index)).hexdigest()[:10]
            at[f"{level}/{index}"] = sid
            entry = sounds.setdefault(sid, {"levels": {}, "owners": [], "length": length(bank, index)})
            entry["levels"].setdefault(str(level), index)
            entry["owners"] = sorted(set(entry["owners"]) | owners.get(index, set()))
    print()
    os.makedirs(CACHE, exist_ok=True)
    with open(CATALOG, "w") as f:
        json.dump({"sounds": sounds, "at": at}, f)
    return sounds, at


def catalog():
    if os.path.exists(CATALOG):
        with open(CATALOG) as f:
            data = json.load(f)
        if "at" in data:
            return data["sounds"], data["at"]
    return build_catalog()


def owner_text(entry):
    names = [OWNERS.get(c, f"class {c:#x}") for c in entry["owners"]]
    return ", ".join(names[:3]) + (f" +{len(names) - 3}" if len(names) > 3 else "") if names else "(the level's)"


def wav_of(sid, entry):
    """The sound rendered to build/sounds/<id>.wav (from the first level that has it)."""
    path = os.path.join(CACHE, f"{sid}.wav")
    if not os.path.exists(path):
        level, index = next(iter(entry["levels"].items()))
        pcm = Bank(source("rc1").read(f"level{level}/sound.bnk")).render(index)
        write_wav(path, pcm or b"\0\0" * (RATE // 50))
    return path


# The running game ------------------------------------------------------------------------------

class Game:
    """The mod's block in a game started under tools/trace.py, if its layout is this build's."""

    def __init__(self):
        self.at, self.why = None, "no game (start it under tools/trace.py)"
        try:
            from live import read, write
            at = find_block(read)
        except Exception as error:             # no tracer, no game: picking still works, saved to the file
            self.why = f"no game ({error.__class__.__name__})"
            return
        if at is None:
            self.why = "no co-op block in the game"
            return
        self.read, self.write = read, write
        constants = {"T_DT": 1 / 60, "T_PI": 3.14159274, "T_ONE": 1.0}
        if any(abs(struct.unpack(">f", read(at + getattr(L, n), 4))[0] - v) > 1e-5 for n, v in constants.items()):
            self.why = "the game runs another build (restart RPCS3 with this one)"
            return
        self.at, self.why = at, ""

    def planet(self):
        return struct.unpack(">I", self.read(PLANET, 4))[0] if self.at else None

    def play_bank(self, index):
        self.write(self.at + L.C_SOUND_TRY, struct.pack(">i", L.SOUND_BANK + index + 1))

    def play_move(self, move):
        tname = dict(L.SOUND_MOVES)[move]
        value = struct.unpack(">i", self.read(self.at + getattr(L, tname), 4))[0]
        self.write(self.at + L.C_SOUND_TRY, struct.pack(">i", value + 1))

    def give(self, move, pick):
        slot = MOVES.index(move)
        levels = [L.SOUND_NONE if i < 0 else i for i in pick["levels"]]
        self.write(self.at + L.SOUND_TABLE + 2 * L.LEVEL_COUNT * slot, struct.pack(f">{L.LEVEL_COUNT}H", *levels))
        self.write(self.at + L.SOUND_VOLUMES + 4 * slot, struct.pack(">I", pick["volume"]))
        self.write(self.at + L.SOUND_SLOT_BANK + 4 * slot, struct.pack(">I", 0))   # (the level's bank, live)
        self.write(self.at + getattr(L, dict(L.SOUND_MOVES)[move]), struct.pack(">i", L.SOUND_OURS + slot))


def find_block(read):
    """The mod's block address (tools/coop.py block, without its exit)."""
    import coop
    data = b""
    for at in range(coop.RW, coop.RW + coop.RW_SIZE, 0x800):
        data += read(at, 0x800)
        found = data.find(coop.TAG)
        if found >= 0:
            return coop.RW + found + len(coop.TAG)
    return None


# Picks -----------------------------------------------------------------------------------------

def load_picks():
    with open(L.SOUND_FILE) as f:
        return json.load(f)


def save_picks(picks):
    with open(L.SOUND_FILE, "w") as f:
        json.dump({move: picks[move] for move in MOVES if move in picks}, f, indent=1)
        f.write("\n")


def pick_of(sid, entry, label, volume):
    return {"id": sid, "label": label, "volume": volume,
            "levels": [entry["levels"].get(str(level), -1) for level in range(L.LEVEL_COUNT)]}


def find_pick(sounds, at, pick):
    """The catalogue's ID of a saved pick (its ID, or the sound at its index on a level it lists)."""
    if pick.get("id") in sounds:
        return pick["id"]
    return next((at.get(f"{lv}/{i}") for lv, i in enumerate(pick["levels"]) if i >= 0), None)


# The browser -----------------------------------------------------------------------------------

class Browser:
    def __init__(self, screen, sounds, at):
        self.screen, self.sounds = screen, sounds
        self.picks = load_picks()
        for pick in self.picks.values():
            pick["id"] = find_pick(sounds, at, pick)
        self.labels = {p["id"]: p["label"] for p in self.picks.values() if p.get("id")}
        self.game = Game()
        self.filter, self.search, self.row, self.top, self.move = 0, "", 0, 0, 0
        self.player, self.dirty = None, False
        self.message = self.game.why or "game found: g plays in it"
        self.refresh_rows()

    def refresh_rows(self):
        planet = self.game.planet() if self.game.at else None
        rows = []
        for sid, entry in self.sounds.items():
            if self.filter == 0 and len(entry["levels"]) < L.LEVEL_COUNT:
                continue
            if self.filter == 1 and (planet is None or str(planet) not in entry["levels"]):
                continue
            text = f"{sid} {owner_text(entry)} {self.labels.get(sid, '')}".lower()
            if self.search and self.search.lower() not in text:
                continue
            rows.append(sid)
        rows.sort(key=lambda sid: (owner_text(self.sounds[sid]) == "(the level's)", owner_text(self.sounds[sid]),
                                   self.sounds[sid]["length"], sid))
        self.rows = rows
        self.row = min(self.row, max(0, len(rows) - 1))

    def say(self, text):
        self.message = text

    def play_here(self, sid):
        if self.player and self.player.poll() is None:
            self.player.terminate()
        self.say(f"rendering {sid} ...")
        self.draw()
        path = wav_of(sid, self.sounds[sid])
        self.player = subprocess.Popen(["pw-play", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.say(f"playing {sid} here ({self.sounds[sid]['length']} s)")

    def play_game(self, sid):
        if not self.game.at:
            return self.say(self.game.why)
        planet = self.game.planet()
        index = self.sounds[sid]["levels"].get(str(planet)) if planet is not None and planet < L.LEVEL_COUNT else None
        if index is None:
            return self.say(f"{sid} is not in {LEVELS[planet] if planet is not None and planet < 19 else 'this level'}'s bank")
        self.game.play_bank(index)
        self.say(f"played {sid} in the game ({LEVELS[planet]}, bank sound {index})")

    def give(self, move, sid):
        entry = self.sounds[sid]
        old = self.picks.get(move, {})
        label = self.labels.get(sid) or owner_text(entry)
        self.picks[move] = pick_of(sid, entry, label, old.get("volume", 0x600))
        self.dirty = True
        missing = L.LEVEL_COUNT - len(entry["levels"])
        live = ""
        if self.game.at:
            self.game.give(move, self.picks[move])
            live = ", live in the game"
        warn = f" - on the {missing} levels without it only after s, a build and a restart" if missing else ""
        self.say(f"{move} <- {sid} ({label}){live}{warn}")

    def volume(self, step):
        move = MOVES[self.move]
        if move not in self.picks:
            return self.say(f"{move} plays a sound of Ratchet's (no pick): give it one first")
        pick = self.picks[move]
        pick["volume"] = max(0x80, min(0x1000, pick["volume"] + step))
        self.dirty = True
        if self.game.at:
            self.game.give(move, pick)
            self.game.play_move(move)
        self.say(f"{move} volume {pick['volume']:#x}" + (" (played in the game)" if self.game.at else ""))

    def ask(self, prompt):
        height, width = self.screen.getmaxyx()
        self.screen.addstr(height - 1, 0, prompt[:width - 1].ljust(width - 1), curses.A_REVERSE)
        curses.echo()
        curses.curs_set(1)
        text = self.screen.getstr(height - 1, min(len(prompt), width - 2)).decode(errors="ignore")
        curses.noecho()
        curses.curs_set(0)
        return text.strip()

    def draw(self):
        s = self.screen
        s.erase()
        height, width = s.getmaxyx()
        put = lambda y, x, text, attr=0: s.addstr(y, x, text[:max(0, width - x - 1)], attr) if 0 <= y < height else None
        put(0, 0, "Clank's sounds   up/down browse  Enter here  g in game  1-6 give to a move  "
                  "Tab move  +/- its volume  t its sound in game  f filter  / search  n name  s save  q quit", curses.A_BOLD)
        x = 0
        for k, move in enumerate(MOVES):
            pick = self.picks.get(move)
            text = f" {k + 1} {move}: {pick['label'][:22]} {pick['volume']:#x} " if pick else f" {k + 1} {move}: (Ratchet's) "
            attr = curses.A_REVERSE if k == self.move else 0
            if x + len(text) >= width:
                break
            put(1, x, text, attr)
            x += len(text) + 1
        planet = self.game.planet() if self.game.at else None
        where = LEVELS[planet] if planet is not None and planet < L.LEVEL_COUNT else "-"
        put(2, 0, f" {FILTERS[self.filter]}  |  {len(self.rows)} sounds  |  search: {self.search or '-'}  |  game: {where}"
                  f"{'  |  unsaved' if self.dirty else ''}", curses.A_DIM)
        put(3, 0, f"   {'ID':<11}{'levels':>6}  {'length':>6}  owner / name")
        lines = height - 6
        if self.row < self.top:
            self.top = self.row
        if self.row >= self.top + lines:
            self.top = self.row - lines + 1
        given = {p.get("id"): move for move, p in self.picks.items()}
        for i, sid in enumerate(self.rows[self.top:self.top + lines]):
            entry = self.sounds[sid]
            mark = f"[{given[sid]}]" if sid in given else ""
            name = self.labels.get(sid, "")
            text = f"{'>' if self.top + i == self.row else ' '} {sid:<11}{len(entry['levels']):>6}  {entry['length']:>5.2f}s  " \
                   f"{owner_text(entry)}{'  ' + name if name else ''} {mark}"
            put(4 + i, 0, text, curses.A_REVERSE if self.top + i == self.row else 0)
        put(height - 2, 0, self.message, curses.A_BOLD)
        s.refresh()

    def run(self):
        curses.curs_set(0)
        while True:
            self.draw()
            key = self.screen.getch()
            sid = self.rows[self.row] if self.rows else None
            if key in (ord("q"), 27):
                if self.dirty and self.ask("unsaved picks: save them? (y/n) ").lower().startswith("y"):
                    save_picks(self.picks)
                return
            elif key in (curses.KEY_DOWN, ord("j")):
                self.row = min(len(self.rows) - 1, self.row + 1)
            elif key in (curses.KEY_UP, ord("k")):
                self.row = max(0, self.row - 1)
            elif key == curses.KEY_NPAGE:
                self.row = min(len(self.rows) - 1, self.row + self.screen.getmaxyx()[0] - 7)
            elif key == curses.KEY_PPAGE:
                self.row = max(0, self.row - self.screen.getmaxyx()[0] + 7)
            elif key == curses.KEY_HOME:
                self.row = 0
            elif key == curses.KEY_END:
                self.row = len(self.rows) - 1
            elif key in (10, 13, curses.KEY_ENTER, ord(" ")) and sid:
                self.play_here(sid)
            elif key == ord("g") and sid:
                self.play_game(sid)
            elif ord("1") <= key < ord("1") + len(MOVES) and sid:
                self.move = key - ord("1")
                self.give(MOVES[self.move], sid)
            elif key == 9:
                self.move = (self.move + 1) % len(MOVES)
            elif key in (ord("+"), ord("=")):
                self.volume(0x80)
            elif key == ord("-"):
                self.volume(-0x80)
            elif key == ord("t"):
                if self.game.at:
                    self.game.play_move(MOVES[self.move])
                    self.say(f"played {MOVES[self.move]}'s sound in the game")
                else:
                    self.say(self.game.why)
            elif key == ord("f"):
                self.filter = (self.filter + 1) % len(FILTERS)
                self.refresh_rows()
            elif key == ord("/"):
                self.search = self.ask("search (owner, ID or name; empty: all): ")
                self.row = 0
                self.refresh_rows()
            elif key == ord("n") and sid:
                name = self.ask(f"name for {sid}: ")
                if name:
                    self.labels[sid] = name
                    for pick in self.picks.values():
                        if pick.get("id") == sid:
                            pick["label"] = name
                            self.dirty = True
            elif key == ord("s"):
                save_picks(self.picks)
                self.dirty = False
                self.say(f"saved to {os.path.relpath(L.SOUND_FILE, ROOT)}: build and install to keep them after a restart")
            elif key == ord("r"):
                self.game = Game()
                self.say(self.game.why or "game found: g plays in it")
                self.refresh_rows()


def main():
    args = sys.argv[1:]
    sounds, at = catalog()
    if not args:
        curses.wrapper(lambda screen: Browser(screen, sounds, at).run())
    elif args[0] == "list":
        which = args[1] if len(args) > 1 else "all"
        planet = Game().planet() if which == "here" else None
        for sid, entry in sorted(sounds.items(), key=lambda kv: (owner_text(kv[1]), kv[0])):
            if which == "all" and len(entry["levels"]) < L.LEVEL_COUNT:
                continue
            if which == "here" and str(planet) not in entry["levels"]:
                continue
            print(f"{sid}  {len(entry['levels']):2} levels  {entry['length']:5.2f}s  {owner_text(entry)}")
    elif args[0] == "play":
        subprocess.run(["pw-play", wav_of(args[1], sounds[args[1]])])
    elif args[0] == "give":
        move, sid = args[1], args[2]
        picks = load_picks()
        old = picks.get(move, {})
        volume = int(args[3], 0) if len(args) > 3 else old.get("volume", 0x600)
        picks[move] = pick_of(sid, sounds[sid], old.get("label") if old.get("id") == sid else owner_text(sounds[sid]), volume)
        save_picks(picks)
        game = Game()
        if game.at:
            game.give(move, picks[move])
        print(f"{move} <- {sid} ({picks[move]['label']}), volume {volume:#x}"
              f"{', live in the game' if game.at else ''}; missing on {picks[move]['levels'].count(-1)} levels")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
