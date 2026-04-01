"""Allow running buddies as: python -m buddies"""

import sys

if "--headless" in sys.argv or "-H" in sys.argv:
    from buddies.headless import run_headless
    run_headless()
else:
    from buddies.app import main
    main()
