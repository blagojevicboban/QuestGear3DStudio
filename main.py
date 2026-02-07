import sys
from PyQt6.QtWidgets import QApplication
from modules.gui import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    print("Application starting...")
    sys.exit(app.exec())
    # print("QuestStream 3D Processor Initialized")

if __name__ == "__main__":
    main()
