import sys


def main():
    if "--refresh" in sys.argv[1:]:
        from FAST import main as refresh_data

        refresh_data()
    else:
        from gui import main as run_gui

        run_gui()


if __name__ == "__main__":
    main()
