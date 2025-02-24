from ip_configurator_gui import MainWindow
from cuprj_cli import parse_ip_library, load_json_file
import sys
from PyQt6.QtWidgets import QApplication

def main():
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