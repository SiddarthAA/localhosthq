"""ridewme cli — headless Python edge daemon (the "driver box").

Barebones skeleton: a placeholder loop. Camera + MediaPipe + signal extraction +
Trust Layer + sensor fusion + signed event emission come later. No UI.
"""

import time


def main() -> None:
    while True:
        print("driver edge daemon")
        time.sleep(1)


if __name__ == "__main__":
    main()
