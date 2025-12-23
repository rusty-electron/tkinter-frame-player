# package entry point. Keep simple: call the main() function implemented in your main.py (moved into package).
def main():
    # import the application module (main.py must be moved into package as tkinter_frame_player.main)
    from . import main as _main
    _main.main()