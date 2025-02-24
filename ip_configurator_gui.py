from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QListWidget, QListWidgetItem, QLabel,
                           QPushButton, QFrame, QLineEdit, QGridLayout, QTabWidget,
                           QSizePolicy, QScrollArea)
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDrag
from dataclasses import dataclass

class IPLibraryWidget(QListWidget):
    def __init__(self, ip_library):
        super().__init__()
        self.setDragEnabled(True)
        self.ip_library = ip_library
        
        for ip_name in ip_library.ip_dict.keys():
            item = QListWidgetItem(ip_name)
            self.addItem(item)

    def startDrag(self, actions):
        item = self.currentItem()
        if item:
            mime_data = QMimeData()
            mime_data.setText(item.text())
            drag = QDrag(self)
            drag.setMimeData(mime_data)
            drag.exec(Qt.DropAction.CopyAction)

class UserProjectSpace(QFrame):
    def __init__(self, ip_library):
        super().__init__()
        self.setAcceptDrops(True)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)
        
        # Add header label
        label = QLabel("User Project Space - Drop IPs here")
        label.setStyleSheet("""
            color: #666666;
            font-size: 16px;
            font-weight: bold;
            padding: 20px;
            background-color: #f5f5f5;
            border-radius: 8px;
        """)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(label)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 2px dashed #cccccc;
                border-radius: 8px;
                background-color: #ffffff;
            }
        """)
        main_layout.addWidget(scroll)
        
        # Create content widget for the grid
        content_widget = QWidget()
        self.grid_layout = QGridLayout(content_widget)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(15, 15, 15, 15)
        
        scroll.setWidget(content_widget)
        
        self.ip_instances = []
        self.ip_library = ip_library

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        ip_name = event.mimeData().text()
        instance_num = len(self.ip_instances)
        row = (instance_num // 2)  # No +1 needed as label is outside grid now
        col = instance_num % 2
        instance = IPInstanceWidget(ip_name, instance_num, self.ip_library)
        self.grid_layout.addWidget(instance, row, col)
        self.ip_instances.append(instance)

    def get_ip_configurations(self):
        configs = []
        for instance in self.ip_instances:
            configs.append({
                'name': f"{instance.ip_name}_{instance.instance_num}",
                'type': instance.ip_name,
                'base_address': instance.base_addr,
                'irq': instance.irq_num,  # Use the modulo-based IRQ number
                'io_pins': instance.get_io_pins()
            })
        return configs

class IPInstanceWidget(QWidget):
    def __init__(self, ip_name: str, instance_num: int, ip_library):
        super().__init__()
        self.ip_name = ip_name
        self.instance_num = instance_num
        self.irq_num = instance_num % 3
        self.base_addr = f"32'h{(0x30000000 + instance_num * 0x10000):08X}"
        self.ip_library = ip_library
        
        # Get IP info
        self.ip_info = ip_library.ip_dict[ip_name].info
        self.external_interfaces = ip_library.ip_dict[ip_name].external_interface
        self.flags = ip_library.ip_dict[ip_name].flags
        self.fifos = ip_library.ip_dict[ip_name].fifos
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        self.setLayout(layout)
        
        # Create IP box
        ip_box = QFrame()
        ip_box.setStyleSheet("""
            QFrame {
                background: #f5f5f5;
                border: 1px solid #dddddd;
                border-radius: 4px;
            }
            QLabel {
                color: #333333;
            }
            QLineEdit {
                background: white;
                border: 1px solid #dddddd;
                border-radius: 2px;
                padding: 2px 4px;
            }
        """)
        
        # Box layout
        box_layout = QVBoxLayout(ip_box)
        box_layout.setContentsMargins(12, 12, 12, 12)
        box_layout.setSpacing(8)
        
        # Header with name and delete button
        header = QHBoxLayout()
        title = QLabel(f"{ip_name} #{instance_num}")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        header.addWidget(title)
        
        delete_button = QPushButton("×")
        delete_button.setFixedSize(20, 20)
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: #dddddd;
                border: none;
                border-radius: 10px;
                color: #666666;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #cccccc;
            }
        """)
        delete_button.clicked.connect(self.deleteLater)
        header.addWidget(delete_button)
        box_layout.addLayout(header)
        
        # Add address
        addr_label = QLabel(f"Base Address: {self.base_addr}")
        addr_label.setStyleSheet("font-family: monospace; color: #666666;")
        box_layout.addWidget(addr_label)
        
        # Add interfaces in a grid
        if self.external_interfaces:
            interfaces_grid = QGridLayout()
            interfaces_grid.setSpacing(4)
            
            for i, interface in enumerate(self.external_interfaces):
                interface_widget = QFrame()
                interface_widget.setStyleSheet("background: white; border: 1px solid #dddddd; border-radius: 2px;")
                interface_layout = QHBoxLayout(interface_widget)
                interface_layout.setContentsMargins(4, 4, 4, 4)
                
                direction = "←" if interface.direction.lower() == "input" else "→"
                name = QLabel(f"{direction} {interface.name}")
                name.setStyleSheet("font-family: monospace; font-size: 12px;")
                interface_layout.addWidget(name)
                
                row = i // 2
                col = i % 2
                interfaces_grid.addWidget(interface_widget, row, col)
            
            box_layout.addLayout(interfaces_grid)
        
        layout.addWidget(ip_box)
        
        # Set fixed size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(350, 250)

    def get_io_pins(self):
        return {interface.name: 10 + self.instance_num for interface in self.external_interfaces}

class MainWindow(QMainWindow):
    def __init__(self, ip_library):
        super().__init__()
        self.ip_library = ip_library
        self.setWindowTitle("IP Configurator")
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        
        # Create horizontal layout for IP library and user project space
        h_layout = QHBoxLayout()
        
        # Create IP library panel with fixed width
        library_panel = QWidget()
        library_panel.setFixedWidth(200)
        library_layout = QVBoxLayout()
        library_panel.setLayout(library_layout)
        library_layout.addWidget(QLabel("Available IPs"))
        library_layout.addWidget(IPLibraryWidget(ip_library))
        
        # Style the IP library panel
        library_panel.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border-radius: 5px;
                padding: 10px;
            }
            QLabel {
                color: #333333;
                font-weight: bold;
                font-size: 14px;
                padding: 5px;
            }
            QListWidget {
                background-color: white;
                border: 1px solid #dddddd;
                border-radius: 3px;
                color: #333333;
                font-family: 'Courier New';
            }
            QListWidget::item:selected {
                background-color: #e6e6e6;
            }
            QListWidget::item:hover {
                background-color: #f0f0f0;
            }
        """)
        
        # Create user project space
        self.user_space = UserProjectSpace(ip_library)
        
        h_layout.addWidget(library_panel)
        h_layout.addWidget(self.user_space, stretch=1)
        main_layout.addLayout(h_layout)
        
        # Add bottom panel with Generate button
        bottom_panel = QHBoxLayout()
        generate_button = QPushButton("Generate Verilog")
        generate_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        generate_button.clicked.connect(self.generate_verilog)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        
        bottom_panel.addWidget(generate_button)
        bottom_panel.addWidget(self.status_label)
        bottom_panel.addStretch()
        main_layout.addLayout(bottom_panel)

        # Set fixed window size
        self.setFixedSize(1200, 800)

    def generate_verilog(self):
        from cuprj_cli import BusGenerator, BusSlaves, BusSlave
        
        configs = self.user_space.get_ip_configurations()
        slaves = [BusSlave(**config) for config in configs]
        bus_slaves = BusSlaves(slaves)
        generator = BusGenerator(bus_slaves, self.ip_library)
        verilog_code = generator.generate_verilog()
        
        filename = 'user_project.v'
        with open(filename, 'w') as f:
            f.write(verilog_code)
            
        self.status_label.setText(f"✓ Generated {filename}") 
        self.status_label.setText(f"✓ Generated {filename}") 