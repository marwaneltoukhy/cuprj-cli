#!/usr/bin/env python3
import sys
from PyQt6.QtWidgets import QApplication

from .core import load_json_file, parse_ip_library
from .gui import MainWindow

def main():
    """Main entry point for the GUI application."""
    app = QApplication(sys.argv)
    
    # Load IP library
    ip_json = load_json_file("ip-lib.json")
    ip_library = parse_ip_library(ip_json)
    
    # Create and show main window
    window = MainWindow(ip_library)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 