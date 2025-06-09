import argparse
import pyautogui
from autoclick_api import load_items, run_workflow


def main():
    parser = argparse.ArgumentParser(description='Run AutoClick workflow from a JSON file')
    parser.add_argument('config', help='JSON workflow file exported from the GUI')
    parser.add_argument('--debug', action='store_true', help='show debug preview windows')
    parser.add_argument('--loop', action='store_true', help='repeat workflow until interrupted')
    parser.add_argument('--interval', type=float, default=0.5, help='delay between loops in seconds')
    parser.add_argument('--disable-failsafe', action='store_true',
                        help='disable PyAutoGUI fail-safe (use with caution)')
    args = parser.parse_args()

    if args.disable_failsafe:
        pyautogui.FAILSAFE = False

    items = load_items(args.config)
    run_workflow(items, debug=args.debug, loop=args.loop, interval=args.interval)


if __name__ == '__main__':
    main()
