# cuprj-cli
Caravel User's Project CLI

## Introduction
This repository contains a Python CLI tool for generating Verilog code for a Wishbone system to be used as a user's project for the Caravel chip. The tool uses a YAML file to define the wishbone bus slaves, and it cross-references these with an IP library provided as a JSON file (by default fetched from GitHub). The generated Verilog code includes a bus splitter, external interface connections, IRQ assignments, and a top-level wrapper module.

## Features

- **Generate Verilog Code**: Process a bus configuration YAML file and an IP library JSON file to generate a complete Verilog module for a Wishbone bus.
- **List Slave Types**: Display a list of all available slave types in the IP library.
- **Display IP Information**: Show key details about a specific slave type, including cell count, interrupt support, FIFO usage, and external interfaces. Optionally display the full description with the `--full` flag.
- **Robust Error Handling**: Provides clear error messages and logging to help troubleshoot issues with input files.
- **CLI Commands**: Supports the `generate`, `list`, `info`, and `help` commands.
- **GUI Interface**: Provides a graphical user interface for drag-and-drop IP configuration.
- **Caravel Integration**: Seamlessly integrates with Caravel user projects, updating the user_project_wrapper.v file and OpenLane configuration.

## Installation

Ensure you have Python 3.9 or later installed. Install the package using pip:

```bash
git clone https://github.com/shalan/cuprj-cli.git
cd cuprj-cli
pip install -e .
```

## CLI Commands

### generate
Generates the Wishbone bus Verilog code using the provided bus YAML file and the IP library JSON.

Usage:

```bash
cuprj generate <bus_yaml_file> [--ip-lib IP_LIBRARY_JSON] [--output-dir OUTPUT_DIR] [--verilog-only] [--header-only] [--caravel-root CARAVEL_ROOT] [--update-openlane] [--create-test] [--test-name TEST_NAME]
```

- bus_yaml_file: Path to the YAML file defining bus slaves.
- --ip-lib: (Optional) Path or URL to the IP library JSON file. If not provided, the default GitHub URL is used.
- --output-dir: (Optional) Output directory (default: current directory).
- --verilog-only: (Optional) Generate only Verilog file.
- --header-only: (Optional) Generate only C header file.
- --caravel-root: (Optional) Path to the caravel_user_project directory for direct integration.
- --update-openlane: (Optional) Update the OpenLane configuration file in the Caravel project.
- --create-test: (Optional) Create a cocotb test in the Caravel project.
- --test-name: (Optional) Name for the cocotb test (default: wb_bus_test).

### list
Lists all slave types available in the IP library.

Usage:

```bash
cuprj list [--ip-library IP_LIBRARY_JSON]
```
- --ip-library: (Optional) Path or URL to the IP library JSON file. If not provided, the default GitHub URL is used.

### info
Displays basic information about a specified slave type from the IP library. By default, it shows the cell count, whether interrupts are supported, FIFO usage, and external interfaces. Use the --full switch to include the full description.

Usage:

```bash
cuprj info <ip_name> [--ip-lib IP_LIBRARY_JSON] [--full]
```
- ip_name: The IP name of the slave type.
- --ip-lib: (Optional) Path or URL to the IP library JSON file. If not provided, the default GitHub URL is used.
- --full: (Optional) Include the full description of the slave type.

### fetch-ips
Fetches IP YAML files from GitHub repositories and aggregates them into a JSON file.

Usage:

```bash
cuprj fetch-ips <input_file> [--output OUTPUT_FILE]
```
- input_file: Path to the text file containing GitHub repository URLs (one per line).
- --output: (Optional) Output JSON file name (default: ip-lib.json).

### gui
Launches the graphical user interface for drag-and-drop IP configuration.

Usage:

```bash
cuprj-gui [--ip-lib IP_LIBRARY_JSON]
```
- --ip-lib: (Optional) Path to the IP library JSON file (default: ip-lib.json).

### caravel
Provides commands for Caravel User Project integration.

Usage:
```bash
cuprj caravel <command> [options]
```

Available commands:
- **update-wrapper**: Update user_project_wrapper.v file
  ```bash
  cuprj caravel update-wrapper <caravel_root> <verilog_file>
  ```
  
- **update-openlane**: Update OpenLane config file
  ```bash
  cuprj caravel update-openlane <caravel_root> <yaml_file> [--ip-lib IP_LIBRARY_JSON]
  ```
  
- **create-test**: Create a cocotb test
  ```bash
  cuprj caravel create-test <caravel_root> <test_name> <yaml_file> [--ip-lib IP_LIBRARY_JSON]
  ```
  
- **run-test**: Run a cocotb test
  ```bash
  cuprj caravel run-test <caravel_root> <test_name> [--simulation-type {rtl,gl,gl-sdf}]
  ```
  
- **run-openlane**: Run OpenLane
  ```bash
  cuprj caravel run-openlane <caravel_root> [--target TARGET]
  ```

### help
Displays the help message with details of all available commands.

Usage:
```bash
cuprj help
```

## Bus YAML File Format

This document describes the structure and content of the YAML file used to define the bus configuration for the Wishbone Bus Generator CLI. The YAML file specifies the list of bus slaves that are attached to the bus. Each slave entry contains key parameters that determine how the slave is connected to the bus, such as its type, base address, I/O pin mappings for external interfaces, and an optional IRQ assignment.

The YAML file should have a top-level key called `slaves`, which contains a list of slave definitions. For example:

```yaml
slaves:
  - name: UART0
    type: EF_UART
    base_address: "32'h30000000"
    io_pins:
      rx: 12
      tx: 13
    irq: 0
  - name: UART1
    type: EF_UART
    base_address: "32'h30010000"
    io_pins:
      rx: 14
      tx: 15
    irq: 1
  - name: PORTA
    type: EF_GPIO8
    base_address: "32'h30020000"
    io_pins:
      io_in: 14
      io_out: 14
      io_oe: 14
    irq: 2
```

## GUI Usage

The GUI provides a user-friendly interface for configuring IPs and integrating with Caravel user projects. To launch the GUI, run:

```bash
cuprj-gui
```

Or:

```bash
cuprj gui
```

### GUI Workflow

1. **Set the Caravel Project Path**:
   - Enter the path to your Caravel user project directory at the top of the window or click "Browse..." to select it.
   - This path will be used for all Caravel integration operations.

2. **Configure IPs**:
   - Drag IPs from the left panel to the user project space.
   - Each IP will be assigned a default base address and IO pins.

3. **Generate Verilog**:
   - Click "Generate Verilog" to create the Wishbone bus module.
   - The `wb_bus.v` file will be saved directly to your project's RTL directory if the project path is set.

4. **Caravel Integration**:
   - Go to the "Caravel Integration" tab to access integration features.
   - Click "Update user_project_wrapper.v" to update the wrapper file with the wb_bus instantiation.
   - Click "Update OpenLane Config" to update the configuration for hardening the design.
   - Click "Run OpenLane" to run the OpenLane flow (requires proper PDK and OpenLane setup).

### Environment Variables

The tool automatically detects and uses the following environment variables:
- `PDK_ROOT`: Path to the PDK directory (defaults to `<caravel_root>/../dependencies/pdks`).
- `OPENLANE_ROOT`: Path to the OpenLane directory (defaults to `<caravel_root>/../dependencies/openlane_src`).

If these variables are not set, the tool will use default paths based on the Caravel project location.

## Disclaimer
This project was developed with the help of ChatGPT o3-mini-high model.