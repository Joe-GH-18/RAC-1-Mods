"""psarc.py <game> <pattern>...: extract the files of a game's PS3arc.psarc whose names contain a
pattern to build/assets/, for looking at them (nothing of it goes into the repository). game is
rc1, rc2 or rc3, next to the RC1 executable as on the Trilogy; the reader is rc2data.py's."""
import os
import sys

from ppu import RC1_ELF

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rc2data import Rc2  # noqa: E402


def main():
    arc = Rc2(os.path.join(os.path.dirname(RC1_ELF), sys.argv[1], "ps3data"))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "assets")
    for pattern in sys.argv[2:]:
        for name in arc.names():
            if pattern in name:
                path = os.path.join(out, name.lstrip("/"))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as f:
                    f.write(arc._from_archive(name))
                print(path)


if __name__ == "__main__":
    main()
