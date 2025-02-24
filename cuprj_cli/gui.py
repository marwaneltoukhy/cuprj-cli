#!/usr/bin/env python3
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QListWidget, QListWidgetItem, QLabel,
                           QPushButton, QFrame, QLineEdit, QGridLayout, QTabWidget,
                           QSizePolicy, QScrollArea, QFileDialog, QMessageBox,
                           QGroupBox, QCheckBox, QComboBox)
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDrag
from dataclasses import dataclass
import os
import sys
import logging
import re

from .core import (
    IPLibrary,
    BusSlaves,
    BusSlave,
    BusGenerator,
)

# Import the new CaravelIntegration class
try:
    from .caravel_integration import CaravelIntegration
except ImportError:
    logging.warning("CaravelIntegration module not found. Caravel integration features will be disabled.")
    CaravelIntegration = None

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

class CaravelSettingsWidget(QWidget):
    """Widget for Caravel integration settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.caravel_root = ""
        self.test_name = "wb_bus_test"
        self.simulation_type = "rtl"
        
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Test Settings
        test_group = QGroupBox("Test Settings")
        test_layout = QGridLayout()
        test_group.setLayout(test_layout)
        
        test_layout.addWidget(QLabel("Test Name:"), 0, 0)
        self.test_name_input = QLineEdit(self.test_name)
        test_layout.addWidget(self.test_name_input, 0, 1)
        
        test_layout.addWidget(QLabel("Simulation Type:"), 1, 0)
        self.sim_type_combo = QComboBox()
        self.sim_type_combo.addItems(["rtl", "gl", "gl-sdf"])
        test_layout.addWidget(self.sim_type_combo, 1, 1)
        
        layout.addWidget(test_group)
        
        # Action Buttons
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout()
        actions_group.setLayout(actions_layout)
        
        self.update_wrapper_button = QPushButton("Update user_project_wrapper.v")
        self.update_wrapper_button.clicked.connect(self._on_update_wrapper)
        actions_layout.addWidget(self.update_wrapper_button)
        
        self.update_openlane_button = QPushButton("Update OpenLane Config")
        self.update_openlane_button.clicked.connect(self._on_update_openlane)
        actions_layout.addWidget(self.update_openlane_button)
        
        self.create_test_button = QPushButton("Create cocotb Test")
        self.create_test_button.clicked.connect(self._on_create_test)
        actions_layout.addWidget(self.create_test_button)
        
        self.run_test_button = QPushButton("Run cocotb Test")
        self.run_test_button.clicked.connect(self._on_run_test)
        actions_layout.addWidget(self.run_test_button)
        
        self.run_openlane_button = QPushButton("Run OpenLane")
        self.run_openlane_button.clicked.connect(self._on_run_openlane)
        actions_layout.addWidget(self.run_openlane_button)
        
        layout.addWidget(actions_group)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Disable buttons initially
        self._update_button_states()
    
    def _update_button_states(self):
        """Update the enabled state of buttons based on current settings."""
        has_caravel_root = bool(self.caravel_root)
        has_caravel_integration = CaravelIntegration is not None
        
        enabled = has_caravel_root and has_caravel_integration
        
        self.update_wrapper_button.setEnabled(enabled)
        self.update_openlane_button.setEnabled(enabled)
        self.create_test_button.setEnabled(enabled)
        self.run_test_button.setEnabled(enabled)
        self.run_openlane_button.setEnabled(enabled)
        
        if not has_caravel_integration:
            self.status_label.setText("Caravel integration module not available")
            self.status_label.setStyleSheet("color: #FF5722; font-weight: bold;")
    
    def _on_update_wrapper(self):
        """Handler for updating the user_project_wrapper.v file."""
        self.status_label.setText("Updating user_project_wrapper.v...")
        self.status_label.setStyleSheet("color: #FFC107; font-weight: bold;")
        # The actual implementation will be handled by the MainWindow
    
    def _on_update_openlane(self):
        """Handler for updating the OpenLane config."""
        self.status_label.setText("Updating OpenLane config...")
        self.status_label.setStyleSheet("color: #FFC107; font-weight: bold;")
        # The actual implementation will be handled by the MainWindow
    
    def _on_create_test(self):
        """Handler for creating a cocotb test."""
        self.status_label.setText("Creating cocotb test...")
        self.status_label.setStyleSheet("color: #FFC107; font-weight: bold;")
        # The actual implementation will be handled by the MainWindow
    
    def _on_run_test(self):
        """Handler for running a cocotb test."""
        self.status_label.setText("Running cocotb test...")
        self.status_label.setStyleSheet("color: #FFC107; font-weight: bold;")
        # The actual implementation will be handled by the MainWindow
    
    def _on_run_openlane(self):
        """Handler for running OpenLane."""
        self.status_label.setText("Running OpenLane...")
        self.status_label.setStyleSheet("color: #FFC107; font-weight: bold;")
        # The actual implementation will be handled by the MainWindow
    
    def get_settings(self):
        """Get the current settings."""
        return {
            "caravel_root": self.caravel_root,
            "test_name": self.test_name_input.text(),
            "simulation_type": self.sim_type_combo.currentText()
        }

class MainWindow(QMainWindow):
    def __init__(self, ip_library):
        super().__init__()
        self.ip_library = ip_library
        self.setWindowTitle("IP Configurator")
        self.project_root = ""
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        
        # Create project path selection at the top
        project_layout = QHBoxLayout()
        project_layout.addWidget(QLabel("Caravel Project Path:"))
        self.project_path_input = QLineEdit()
        self.project_path_input.setPlaceholderText("Path to caravel_user_project directory")
        project_layout.addWidget(self.project_path_input)
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_project_directory)
        project_layout.addWidget(browse_button)
        
        main_layout.addLayout(project_layout)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create IP Configuration tab
        ip_config_tab = QWidget()
        ip_config_layout = QVBoxLayout()
        ip_config_tab.setLayout(ip_config_layout)
        
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
        ip_config_layout.addLayout(h_layout)
        
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
        
        self.ip_config_status_label = QLabel("")
        self.ip_config_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        
        bottom_panel.addWidget(generate_button)
        bottom_panel.addWidget(self.ip_config_status_label)
        bottom_panel.addStretch()
        ip_config_layout.addLayout(bottom_panel)
        
        # Add IP Configuration tab
        self.tab_widget.addTab(ip_config_tab, "IP Configuration")
        
        # Create Caravel Integration tab if the module is available
        if CaravelIntegration is not None:
            self.caravel_tab = CaravelSettingsWidget()
            self.tab_widget.addTab(self.caravel_tab, "Caravel Integration")
            
            # Connect signals
            self.caravel_tab.update_wrapper_button.clicked.connect(self.update_user_project_wrapper)
            self.caravel_tab.update_openlane_button.clicked.connect(self.update_openlane_config)
            self.caravel_tab.create_test_button.clicked.connect(self.create_cocotb_test)
            self.caravel_tab.run_test_button.clicked.connect(self.run_cocotb_test)
            self.caravel_tab.run_openlane_button.clicked.connect(self.run_openlane)
            
            # Connect project path changes
            self.project_path_input.textChanged.connect(self._update_caravel_path)
        
        # Set fixed window size
        self.setFixedSize(1200, 800)
        
        # Store the generated Verilog code
        self.generated_verilog = None
        self.module_names = []
        self.cell_counts = {}
    
    def _browse_project_directory(self):
        """Open a file dialog to select the caravel_user_project directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Caravel User Project Directory", ""
        )
        if directory:
            self.project_path_input.setText(directory)
            self.project_root = directory
            self._update_caravel_path()
    
    def _update_caravel_path(self):
        """Update the Caravel path in the Caravel tab."""
        if hasattr(self, 'caravel_tab'):
            self.project_root = self.project_path_input.text()
            self.caravel_tab.caravel_root = self.project_root
            self.caravel_tab._update_button_states()

    def generate_verilog(self):
        from .core import BusGenerator, BusSlaves, BusSlave, generate_wrapper
        
        configs = self.user_space.get_ip_configurations()
        if not configs:
            QMessageBox.warning(self, "No IPs", "Please add at least one IP to the design.")
            return
        
        # Check if project path is set
        if not self.project_root:
            # Ask if user wants to set the project path or just save to a custom directory
            reply = QMessageBox.question(
                self, 
                "Project Path Not Set", 
                "The Caravel project path is not set. Would you like to set it now?\n\n"
                "Click 'Yes' to set the project path.\n"
                "Click 'No' to select a custom output directory.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._browse_project_directory()
                if not self.project_root:
                    return  # User cancelled
            else:
                # Ask for output directory
                output_dir = QFileDialog.getExistingDirectory(
                    self, "Select Output Directory", ""
                )
                if not output_dir:
                    return  # User cancelled
        
        # Generate the Verilog code
        slaves = [BusSlave(**config) for config in configs]
        bus_slaves = BusSlaves(slaves)
        generator = BusGenerator(bus_slaves, self.ip_library)
        verilog_code = generator.generate_verilog()
        wrapper_code = generate_wrapper(verilog_code)
        
        # Store the generated code and module information
        self.generated_verilog = wrapper_code
        self.module_names = [slave.type for slave in slaves]
        self.cell_counts = {slave.type: generator.processed_slaves[i].cell_count 
                           for i, slave in enumerate(slaves)}
        
        # Extract just the wb_bus module
        wb_bus_module_match = re.search(r'(module wb_bus\s*\([^;]*\);.*?endmodule)', wrapper_code, re.DOTALL)
        if not wb_bus_module_match:
            QMessageBox.critical(self, "Error", "Could not extract wb_bus module from generated code.")
            return
        
        wb_bus_code = wb_bus_module_match.group(1)
        
        # Save the files
        if self.project_root:
            # Save directly to the project's verilog/rtl directory
            rtl_dir = os.path.join(self.project_root, 'verilog', 'rtl')
            if not os.path.exists(rtl_dir):
                os.makedirs(rtl_dir, exist_ok=True)
            
            wb_bus_file = os.path.join(rtl_dir, 'wb_bus.v')
            with open(wb_bus_file, 'w') as f:
                f.write(wb_bus_code)
            
            self.ip_config_status_label.setText(f"✓ Generated and saved to {wb_bus_file}")
            
            QMessageBox.information(self, "Verilog Generated", 
                                   f"wb_bus.v has been generated and saved to the project's RTL directory.")
        else:
            # Save to the selected directory
            output_dir = QFileDialog.getExistingDirectory(
                self, "Select Output Directory", ""
            )
            if not output_dir:
                return  # User cancelled
            
            filename = os.path.join(output_dir, 'wb_bus.v')
            with open(filename, 'w') as f:
                f.write(wb_bus_code)
            
            # Also save the full wrapper for reference
            wrapper_filename = os.path.join(output_dir, 'user_project_wrapper_reference.v')
            with open(wrapper_filename, 'w') as f:
                f.write(wrapper_code)
            
            self.ip_config_status_label.setText(f"✓ Generated {filename}")
            
            QMessageBox.information(self, "Verilog Generated", 
                                   f"wb_bus.v has been generated and saved to {filename}.\n\n"
                                   f"A reference user_project_wrapper.v has also been saved to {wrapper_filename}.")
    
    def update_user_project_wrapper(self):
        """Update the user_project_wrapper.v file in the Caravel project."""
        if not self.generated_verilog:
            QMessageBox.warning(self, "No Verilog Generated", 
                               "Please generate Verilog code first in the IP Configuration tab.")
            return
        
        if not self.project_root:
            QMessageBox.warning(self, "Project Path Not Set", 
                               "Please set the Caravel project path first.")
            return
        
        try:
            integration = CaravelIntegration(self.project_root)
            integration.update_user_project_wrapper(self.generated_verilog)
            
            self.caravel_tab.status_label.setText("✓ Updated user_project_wrapper.v")
            self.caravel_tab.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            
            QMessageBox.information(self, "Update Successful", 
                                   "Successfully updated user_project_wrapper.v in the Caravel project.")
        except Exception as e:
            self.caravel_tab.status_label.setText(f"✗ Error: {str(e)}")
            self.caravel_tab.status_label.setStyleSheet("color: #F44336; font-weight: bold;")
            
            QMessageBox.critical(self, "Update Failed", 
                                f"Failed to update user_project_wrapper.v: {str(e)}")
    
    def update_openlane_config(self):
        """Update the OpenLane config.tcl file in the Caravel project."""
        if not self.module_names:
            QMessageBox.warning(self, "No Modules", 
                               "Please generate Verilog code first in the IP Configuration tab.")
            return
        
        if not self.project_root:
            QMessageBox.warning(self, "Project Path Not Set", 
                               "Please set the Caravel project path first.")
            return
        
        try:
            integration = CaravelIntegration(self.project_root)
            integration.update_openlane_config(self.module_names, self.cell_counts)
            
            self.caravel_tab.status_label.setText("✓ Updated OpenLane config")
            self.caravel_tab.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            
            QMessageBox.information(self, "Update Successful", 
                                   "Successfully updated OpenLane config in the Caravel project.")
        except Exception as e:
            self.caravel_tab.status_label.setText(f"✗ Error: {str(e)}")
            self.caravel_tab.status_label.setStyleSheet("color: #F44336; font-weight: bold;")
            
            QMessageBox.critical(self, "Update Failed", 
                                f"Failed to update OpenLane config: {str(e)}")
    
    def create_cocotb_test(self):
        """Create a cocotb test in the Caravel project."""
        if not self.module_names:
            QMessageBox.warning(self, "No Modules", 
                               "Please generate Verilog code first in the IP Configuration tab.")
            return
        
        if not self.project_root:
            QMessageBox.warning(self, "Project Path Not Set", 
                               "Please set the Caravel project path first.")
            return
        
        settings = self.caravel_tab.get_settings()
        test_name = settings["test_name"]
        
        try:
            integration = CaravelIntegration(self.project_root)
            integration.create_cocotb_test(test_name, self.module_names)
            
            self.caravel_tab.status_label.setText(f"✓ Created cocotb test: {test_name}")
            self.caravel_tab.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            
            QMessageBox.information(self, "Test Created", 
                                   f"Successfully created cocotb test '{test_name}' in the Caravel project.")
        except Exception as e:
            self.caravel_tab.status_label.setText(f"✗ Error: {str(e)}")
            self.caravel_tab.status_label.setStyleSheet("color: #F44336; font-weight: bold;")
            
            QMessageBox.critical(self, "Test Creation Failed", 
                                f"Failed to create cocotb test: {str(e)}")
    
    def run_cocotb_test(self):
        """Run a cocotb test in the Caravel project."""
        if not self.project_root:
            QMessageBox.warning(self, "Project Path Not Set", 
                               "Please set the Caravel project path first.")
            return
        
        settings = self.caravel_tab.get_settings()
        test_name = settings["test_name"]
        simulation_type = settings["simulation_type"]
        
        try:
            integration = CaravelIntegration(self.project_root)
            success = integration.run_cocotb_test(test_name, simulation_type)
            
            if success:
                self.caravel_tab.status_label.setText(f"✓ Test {test_name} passed")
                self.caravel_tab.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
                
                QMessageBox.information(self, "Test Passed", 
                                       f"The cocotb test '{test_name}' ({simulation_type}) passed successfully.")
            else:
                self.caravel_tab.status_label.setText(f"✗ Test {test_name} failed")
                self.caravel_tab.status_label.setStyleSheet("color: #F44336; font-weight: bold;")
                
                QMessageBox.warning(self, "Test Failed", 
                                   f"The cocotb test '{test_name}' ({simulation_type}) failed.")
        except Exception as e:
            self.caravel_tab.status_label.setText(f"✗ Error: {str(e)}")
            self.caravel_tab.status_label.setStyleSheet("color: #F44336; font-weight: bold;")
            
            QMessageBox.critical(self, "Test Run Failed", 
                                f"Failed to run cocotb test: {str(e)}")
    
    def run_openlane(self):
        """Run OpenLane in the Caravel project."""
        if not self.project_root:
            QMessageBox.warning(self, "Project Path Not Set", 
                               "Please set the Caravel project path first.")
            return
        
        # Check if the wb_bus.v file exists in the Caravel RTL directory
        wb_bus_file = os.path.join(self.project_root, 'verilog', 'rtl', 'wb_bus.v')
        if not os.path.exists(wb_bus_file):
            error_msg = "The wb_bus.v file does not exist in the Caravel RTL directory.\n\n"
            error_msg += "Please generate the Verilog code first."
            
            self.caravel_tab.status_label.setText(f"✗ Error: wb_bus.v not found")
            self.caravel_tab.status_label.setStyleSheet("color: #F44336; font-weight: bold;")
            
            QMessageBox.critical(self, "File Not Found", error_msg)
            return
        
        # Determine default PDK_ROOT and OPENLANE_ROOT paths
        default_pdk_root = os.path.join(os.path.dirname(self.project_root), "dependencies/pdks")
        default_openlane_root = os.path.join(os.path.dirname(self.project_root), "dependencies/openlane_src")
        
        # Check if the default directories exist
        pdk_exists = os.path.exists(default_pdk_root)
        openlane_exists = os.path.exists(default_openlane_root)
        
        # Prepare environment variables info for the confirmation dialog
        env_info = "Environment variables:\n"
        if "PDK_ROOT" in os.environ:
            env_info += f"- PDK_ROOT: {os.environ['PDK_ROOT']} (from environment)\n"
        elif pdk_exists:
            env_info += f"- PDK_ROOT: {default_pdk_root} (default location)\n"
        else:
            env_info += f"- PDK_ROOT: {default_pdk_root} (default location, NOT FOUND)\n"
            
        if "OPENLANE_ROOT" in os.environ:
            env_info += f"- OPENLANE_ROOT: {os.environ['OPENLANE_ROOT']} (from environment)\n"
        elif openlane_exists:
            env_info += f"- OPENLANE_ROOT: {default_openlane_root} (default location)\n"
        else:
            env_info += f"- OPENLANE_ROOT: {default_openlane_root} (default location, NOT FOUND)\n"
        
        # Confirm with the user
        msg = "Running OpenLane can take a long time and requires proper setup.\n\n"
        msg += "Make sure you have:\n"
        msg += "1. Generated and saved the wb_bus.v file to the Caravel RTL directory\n"
        msg += "2. Updated the user_project_wrapper.v file\n"
        msg += "3. Updated the OpenLane configuration\n\n"
        msg += env_info + "\n"
        
        if not pdk_exists and "PDK_ROOT" not in os.environ:
            msg += "WARNING: Default PDK directory not found. Please install the PDK or set PDK_ROOT.\n\n"
            
        if not openlane_exists and "OPENLANE_ROOT" not in os.environ:
            msg += "WARNING: Default OpenLane directory not found. Please install OpenLane or set OPENLANE_ROOT.\n\n"
            
        msg += "Do you want to continue?"
        
        reply = QMessageBox.question(self, "Run OpenLane", msg, 
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        self.caravel_tab.status_label.setText("Running OpenLane... (this may take a while)")
        self.caravel_tab.status_label.setStyleSheet("color: #FFC107; font-weight: bold;")
        QApplication.processEvents()  # Update the UI
        
        try:
            integration = CaravelIntegration(self.project_root)
            success = integration.run_openlane()
            
            if success:
                self.caravel_tab.status_label.setText("✓ OpenLane run completed successfully")
                self.caravel_tab.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
                
                QMessageBox.information(self, "OpenLane Success", 
                                       "OpenLane completed successfully.")
            else:
                self.caravel_tab.status_label.setText("✗ OpenLane run failed")
                self.caravel_tab.status_label.setStyleSheet("color: #F44336; font-weight: bold;")
                
                error_msg = "OpenLane run failed. This could be due to:\n\n"
                error_msg += "1. Missing or incorrect PDK setup\n"
                error_msg += "2. Missing or incorrect OpenLane setup\n"
                error_msg += "3. Issues with the Verilog code or configuration\n\n"
                error_msg += "Please check the console output for details."
                
                QMessageBox.warning(self, "OpenLane Failed", error_msg)
        except Exception as e:
            self.caravel_tab.status_label.setText(f"✗ Error: {str(e)}")
            self.caravel_tab.status_label.setStyleSheet("color: #F44336; font-weight: bold;")
            
            QMessageBox.critical(self, "OpenLane Run Failed", 
                                f"Failed to run OpenLane: {str(e)}") 