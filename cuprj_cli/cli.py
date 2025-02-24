#!/usr/bin/env python3
import sys
import os
import argparse
import logging
from typing import Any, Dict, List, Optional, Union, Tuple

from .core import (
    DEFAULT_IPS_URL,
    IPLibrary,
    BusSlaves,
    BusGenerator,
    load_json_file,
    load_yaml_file,
    parse_ip_library,
    parse_bus_slaves,
    generate_wrapper,
    generate_c_header,
    parse_repo_url,
    fetch_yaml_from_repo,
)

# Import the new CaravelIntegration class
try:
    from .caravel_integration import CaravelIntegration
    CARAVEL_INTEGRATION_AVAILABLE = True
except ImportError:
    logging.warning("CaravelIntegration module not found. Caravel integration commands will be disabled.")
    CARAVEL_INTEGRATION_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def generate_command(args: argparse.Namespace) -> None:
    """Generate Verilog and C header files from a YAML configuration.

    Args:
        args: Command line arguments.
    """
    yaml_file = args.yaml_file
    ip_lib = args.ip_lib
    output_dir = args.output_dir
    
    # Load IP library
    ip_json = load_json_file(ip_lib)
    ip_library = parse_ip_library(ip_json)
    
    # Load bus slaves configuration
    bus_yaml = load_yaml_file(yaml_file)
    bus_slaves = parse_bus_slaves(bus_yaml)
    
    # Generate Verilog code
    generator = BusGenerator(bus_slaves, ip_library)
    
    if not args.header_only:
        verilog_code = generator.generate_verilog()
        wrapper_code = generate_wrapper(verilog_code)
        
        # Write Verilog file
        verilog_file = os.path.join(output_dir, "wb_bus.v")
        with open(verilog_file, "w") as f:
            f.write(wrapper_code)
        logging.info(f"Generated Verilog file: {verilog_file}")
    
    if not args.verilog_only:
        # Generate C header
        header_code = generate_c_header(generator, yaml_file)
        
        # Write C header file
        header_file = os.path.join(output_dir, "wb_bus.h")
        with open(header_file, "w") as f:
            f.write(header_code)
        logging.info(f"Generated C header file: {header_file}")
    
    # If caravel integration is requested, update the user_project_wrapper.v file
    if args.caravel_root and CARAVEL_INTEGRATION_AVAILABLE:
        try:
            caravel = CaravelIntegration(args.caravel_root)
            
            # Update user_project_wrapper.v
            if not args.header_only:
                caravel.update_user_project_wrapper(wrapper_code)
                logging.info(f"Updated user_project_wrapper.v in {args.caravel_root}")
            
            # Update OpenLane config if requested
            if args.update_openlane:
                module_names = [slave.type for slave in bus_slaves.slaves]
                cell_counts = {slave.type: generator.processed_slaves[i].cell_count 
                              for i, slave in enumerate(bus_slaves.slaves)}
                caravel.update_openlane_config(module_names, cell_counts)
                logging.info(f"Updated OpenLane config in {args.caravel_root}")
            
            # Create cocotb test if requested
            if args.create_test:
                module_names = [slave.type for slave in bus_slaves.slaves]
                caravel.create_cocotb_test(args.test_name, module_names)
                logging.info(f"Created cocotb test '{args.test_name}' in {args.caravel_root}")
                
        except Exception as e:
            logging.error(f"Error during Caravel integration: {e}")
            sys.exit(1)


def list_command(args: argparse.Namespace) -> None:
    """Executes the list command.

    Args:
        args (argparse.Namespace): Command-line arguments.
    """
    ip_library_source: str = args.ip_library if args.ip_library else DEFAULT_IPS_URL
    ip_json = load_json_file(ip_library_source)
    ip_library = parse_ip_library(ip_json)
    logging.info("Available slave types in the IP library:")
    for ip_name in ip_library.ip_dict.keys():
        print(f"  - {ip_name}")


def info_command(args: argparse.Namespace) -> None:
    """Executes the info command.

    Args:
        args (argparse.Namespace): Command-line arguments.
    """
    slave_type: str = args.ip_name
    ip_library_source: str = args.ip_lib if args.ip_lib else DEFAULT_IPS_URL
    ip_json = load_json_file(ip_library_source)
    ip_library = parse_ip_library(ip_json)
    entry = ip_library.ip_dict.get(slave_type)
    if entry is None:
        logging.error(f"Slave type '{slave_type}' not found in the IP library.")
        sys.exit(1)
    info = entry.info
    wb_cell_count: Union[str, int] = "N/A"
    for cell in info.cell_count:
        if "WB" in cell:
            wb_cell_count = cell["WB"]
            break
    interrupts: str = "Yes" if entry.flags is not None else "No"
    fifos: str = "Yes" if entry.fifos and len(entry.fifos) > 0 else "No"
    if entry.external_interface:
        interfaces = [f"{iface.name} ({iface.direction})" for iface in entry.external_interface]
        ext_if_str = ", ".join(interfaces)
    else:
        ext_if_str = "None"
    print(f"Information for {slave_type}:")
    print(f"  Cell count: {wb_cell_count}")
    print(f"  Interrupts Supported: {interrupts}")
    print(f"  FIFO Usage: {fifos}")
    print(f"  External Interfaces: {ext_if_str}")
    if args.full:
        print(f"  Description: {info.description}")


def help_command(parser: argparse.ArgumentParser) -> None:
    """Executes the help command.

    Args:
        parser (argparse.ArgumentParser): The top-level argument parser.
    """
    print(parser.format_help())
    sys.exit(0)


def fetch_ips_command(args: argparse.Namespace) -> None:
    """
    Fetches IP YAML files from GitHub repositories and aggregates them into a JSON file.
    
    Args:
        args: Command line arguments containing the input file and output file.
    """
    input_file = args.input_file
    output_file = args.output
    
    if not os.path.exists(input_file):
        logging.error(f"Input file '{input_file}' not found.")
        return
    
    with open(input_file, "r") as f:
        repo_urls = [line.strip() for line in f if line.strip()]
    
    aggregated_slaves = []  # This list will store the parsed YAML content from each repo

    for url in repo_urls:
        owner, repo = parse_repo_url(url)
        if not owner or not repo:
            logging.error(f"Could not parse repository information from URL: {url}")
            continue

        logging.info(f"Processing repository: {owner}/{repo}")
        result = fetch_yaml_from_repo(owner, repo)
        if result:
            file_name, content = result
            try:
                import yaml
                parsed_yaml = yaml.safe_load(content)
                aggregated_slaves.append(parsed_yaml)
                logging.info(f"Parsed YAML from {owner}/{repo} ({file_name}).")
            except yaml.YAMLError as e:
                logging.error(f"Error parsing YAML from {owner}/{repo} ({file_name}): {e}")
        logging.info("-" * 40)
    
    # Aggregate the parsed YAML into a JSON structure under the key 'slaves'
    aggregated_data = {"slaves": aggregated_slaves}
    
    import json
    with open(output_file, "w", encoding="utf-8") as out_file:
        json.dump(aggregated_data, out_file, indent=4, default=str)
    
    logging.info(f"\nAggregated JSON file saved as: {output_file}")


def launch_gui(args: argparse.Namespace) -> None:
    """
    Launch the graphical user interface.
    
    Args:
        args: Command line arguments containing the IP library file.
    """
    try:
        from PyQt6.QtWidgets import QApplication
        from .gui import MainWindow
    except ImportError:
        logging.error("PyQt6 is required for the GUI. Install it with: pip install PyQt6")
        sys.exit(1)
        
    app = QApplication(sys.argv)
    
    # Load IP library
    ip_json = load_json_file(args.ip_lib)
    ip_library = parse_ip_library(ip_json)
    
    # Create and show main window
    window = MainWindow(ip_library)
    window.show()
    
    sys.exit(app.exec())


def caravel_update_wrapper_command(args: argparse.Namespace) -> None:
    """
    Update the user_project_wrapper.v file in a Caravel User Project.
    
    Args:
        args: Command line arguments containing the Caravel root directory and Verilog file.
    """
    if not CARAVEL_INTEGRATION_AVAILABLE:
        logging.error("Caravel integration module not available.")
        sys.exit(1)
    
    caravel_root = args.caravel_root
    verilog_file = args.verilog_file
    
    try:
        # Read the Verilog file
        with open(verilog_file, "r") as f:
            verilog_code = f.read()
        
        # Update the user_project_wrapper.v file
        caravel = CaravelIntegration(caravel_root)
        caravel.update_user_project_wrapper(verilog_code)
        
        logging.info(f"Updated user_project_wrapper.v in {caravel_root}")
    except Exception as e:
        logging.error(f"Error updating user_project_wrapper.v: {e}")
        sys.exit(1)


def caravel_update_openlane_command(args: argparse.Namespace) -> None:
    """
    Update the OpenLane config.tcl file in a Caravel User Project.
    
    Args:
        args: Command line arguments containing the Caravel root directory and YAML file.
    """
    if not CARAVEL_INTEGRATION_AVAILABLE:
        logging.error("Caravel integration module not available.")
        sys.exit(1)
    
    caravel_root = args.caravel_root
    yaml_file = args.yaml_file
    ip_lib = args.ip_lib
    
    try:
        # Load IP library
        ip_json = load_json_file(ip_lib)
        ip_library = parse_ip_library(ip_json)
        
        # Load bus slaves configuration
        bus_yaml = load_yaml_file(yaml_file)
        bus_slaves = parse_bus_slaves(bus_yaml)
        
        # Generate Verilog code to get cell counts
        generator = BusGenerator(bus_slaves, ip_library)
        
        # Get module names and cell counts
        module_names = [slave.type for slave in bus_slaves.slaves]
        cell_counts = {slave.type: generator.processed_slaves[i].cell_count 
                      for i, slave in enumerate(bus_slaves.slaves)}
        
        # Update the OpenLane config.tcl file
        caravel = CaravelIntegration(caravel_root)
        caravel.update_openlane_config(module_names, cell_counts)
        
        logging.info(f"Updated OpenLane config in {caravel_root}")
    except Exception as e:
        logging.error(f"Error updating OpenLane config: {e}")
        sys.exit(1)


def caravel_create_test_command(args: argparse.Namespace) -> None:
    """
    Create a cocotb test in a Caravel User Project.
    
    Args:
        args: Command line arguments containing the Caravel root directory, test name, and YAML file.
    """
    if not CARAVEL_INTEGRATION_AVAILABLE:
        logging.error("Caravel integration module not available.")
        sys.exit(1)
    
    caravel_root = args.caravel_root
    test_name = args.test_name
    yaml_file = args.yaml_file
    ip_lib = args.ip_lib
    
    try:
        # Load IP library
        ip_json = load_json_file(ip_lib)
        ip_library = parse_ip_library(ip_json)
        
        # Load bus slaves configuration
        bus_yaml = load_yaml_file(yaml_file)
        bus_slaves = parse_bus_slaves(bus_yaml)
        
        # Get module names
        module_names = [slave.type for slave in bus_slaves.slaves]
        
        # Create the cocotb test
        caravel = CaravelIntegration(caravel_root)
        caravel.create_cocotb_test(test_name, module_names)
        
        logging.info(f"Created cocotb test '{test_name}' in {caravel_root}")
    except Exception as e:
        logging.error(f"Error creating cocotb test: {e}")
        sys.exit(1)


def caravel_run_test_command(args: argparse.Namespace) -> None:
    """
    Run a cocotb test in a Caravel User Project.
    
    Args:
        args: Command line arguments containing the Caravel root directory, test name, and simulation type.
    """
    if not CARAVEL_INTEGRATION_AVAILABLE:
        logging.error("Caravel integration module not available.")
        sys.exit(1)
    
    caravel_root = args.caravel_root
    test_name = args.test_name
    simulation_type = args.simulation_type
    
    try:
        # Run the cocotb test
        caravel = CaravelIntegration(caravel_root)
        success = caravel.run_cocotb_test(test_name, simulation_type)
        
        if success:
            logging.info(f"Test '{test_name}' ({simulation_type}) passed!")
        else:
            logging.error(f"Test '{test_name}' ({simulation_type}) failed.")
            sys.exit(1)
    except Exception as e:
        logging.error(f"Error running cocotb test: {e}")
        sys.exit(1)


def caravel_run_openlane_command(args: argparse.Namespace) -> None:
    """
    Run OpenLane in a Caravel User Project.
    
    Args:
        args: Command line arguments containing the Caravel root directory and target.
    """
    if not CARAVEL_INTEGRATION_AVAILABLE:
        logging.error("Caravel integration module not available.")
        sys.exit(1)
    
    caravel_root = args.caravel_root
    target = args.target
    
    try:
        # Run OpenLane
        caravel = CaravelIntegration(caravel_root)
        success = caravel.run_openlane(target)
        
        if success:
            logging.info(f"OpenLane run for '{target}' completed successfully!")
        else:
            logging.error(f"OpenLane run for '{target}' failed.")
            sys.exit(1)
    except Exception as e:
        logging.error(f"Error running OpenLane: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="CUPRJ CLI - A tool for generating Verilog and C headers for Caravel User Project bus configurations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate Verilog and C header files")
    generate_parser.add_argument("yaml_file", help="YAML configuration file")
    generate_parser.add_argument(
        "--ip-lib", 
        default=DEFAULT_IPS_URL,
        help=f"IP library JSON file or URL (default: {DEFAULT_IPS_URL})"
    )
    generate_parser.add_argument(
        "--output-dir", 
        default=".",
        help="Output directory (default: current directory)"
    )
    generate_parser.add_argument(
        "--verilog-only", 
        action="store_true",
        help="Generate only Verilog file"
    )
    generate_parser.add_argument(
        "--header-only", 
        action="store_true",
        help="Generate only C header file"
    )
    # Add Caravel integration options
    if CARAVEL_INTEGRATION_AVAILABLE:
        generate_parser.add_argument(
            "--caravel-root",
            help="Path to the caravel_user_project directory for direct integration"
        )
        generate_parser.add_argument(
            "--update-openlane",
            action="store_true",
            help="Update the OpenLane config.tcl file in the Caravel project"
        )
        generate_parser.add_argument(
            "--create-test",
            action="store_true",
            help="Create a cocotb test in the Caravel project"
        )
        generate_parser.add_argument(
            "--test-name",
            default="wb_bus_test",
            help="Name for the cocotb test (default: wb_bus_test)"
        )
    generate_parser.set_defaults(func=generate_command)

    # List command
    list_parser = subparsers.add_parser("list", help="List available IPs")
    list_parser.add_argument(
        "--ip-library", 
        default=DEFAULT_IPS_URL,
        help=f"IP library JSON file or URL (default: {DEFAULT_IPS_URL})"
    )
    list_parser.set_defaults(func=list_command)

    # Info command
    info_parser = subparsers.add_parser("info", help="Show information about a specific IP")
    info_parser.add_argument("ip_name", help="Name of the IP")
    info_parser.add_argument(
        "--ip-lib", 
        default=DEFAULT_IPS_URL,
        help=f"IP library JSON file or URL (default: {DEFAULT_IPS_URL})"
    )
    info_parser.add_argument(
        "--full", 
        action="store_true",
        help="Show full description"
    )
    info_parser.set_defaults(func=info_command)
    
    # Fetch IPs command
    fetch_parser = subparsers.add_parser("fetch-ips", help="Fetch IP YAML files from GitHub repositories")
    fetch_parser.add_argument(
        "input_file", 
        help="Path to the text file containing GitHub repository URLs (one per line)"
    )
    fetch_parser.add_argument(
        "-o", "--output",
        default="ip-lib.json",
        help="Output JSON file name (default: ip-lib.json)"
    )
    fetch_parser.set_defaults(func=fetch_ips_command)

    # Help command
    help_parser = subparsers.add_parser("help", help="Show help for a specific command")
    help_parser.set_defaults(func=lambda _: help_command(parser))

    # GUI command
    gui_parser = subparsers.add_parser("gui", help="Launch the graphical user interface")
    gui_parser.add_argument(
        "--ip-lib", 
        default="ip-lib.json",
        help="IP library JSON file (default: ip-lib.json)"
    )
    gui_parser.set_defaults(func=launch_gui)
    
    # Caravel integration commands
    if CARAVEL_INTEGRATION_AVAILABLE:
        caravel_parser = subparsers.add_parser("caravel", help="Caravel User Project integration commands")
        caravel_subparsers = caravel_parser.add_subparsers(dest="caravel_command", help="Caravel command to execute")
        
        # Update user_project_wrapper.v command
        update_wrapper_parser = caravel_subparsers.add_parser("update-wrapper", help="Update user_project_wrapper.v file")
        update_wrapper_parser.add_argument("caravel_root", help="Path to the caravel_user_project directory")
        update_wrapper_parser.add_argument("verilog_file", help="Verilog file to use for updating user_project_wrapper.v")
        update_wrapper_parser.set_defaults(func=caravel_update_wrapper_command)
        
        # Update OpenLane config command
        update_openlane_parser = caravel_subparsers.add_parser("update-openlane", help="Update OpenLane config.tcl file")
        update_openlane_parser.add_argument("caravel_root", help="Path to the caravel_user_project directory")
        update_openlane_parser.add_argument("yaml_file", help="YAML configuration file")
        update_openlane_parser.add_argument(
            "--ip-lib", 
            default=DEFAULT_IPS_URL,
            help=f"IP library JSON file or URL (default: {DEFAULT_IPS_URL})"
        )
        update_openlane_parser.set_defaults(func=caravel_update_openlane_command)
        
        # Create cocotb test command
        create_test_parser = caravel_subparsers.add_parser("create-test", help="Create a cocotb test")
        create_test_parser.add_argument("caravel_root", help="Path to the caravel_user_project directory")
        create_test_parser.add_argument("test_name", help="Name for the cocotb test")
        create_test_parser.add_argument("yaml_file", help="YAML configuration file")
        create_test_parser.add_argument(
            "--ip-lib", 
            default=DEFAULT_IPS_URL,
            help=f"IP library JSON file or URL (default: {DEFAULT_IPS_URL})"
        )
        create_test_parser.set_defaults(func=caravel_create_test_command)
        
        # Run cocotb test command
        run_test_parser = caravel_subparsers.add_parser("run-test", help="Run a cocotb test")
        run_test_parser.add_argument("caravel_root", help="Path to the caravel_user_project directory")
        run_test_parser.add_argument("test_name", help="Name of the cocotb test to run")
        run_test_parser.add_argument(
            "--simulation-type",
            choices=["rtl", "gl", "gl-sdf"],
            default="rtl",
            help="Type of simulation to run (default: rtl)"
        )
        run_test_parser.set_defaults(func=caravel_run_test_command)
        
        # Run OpenLane command
        run_openlane_parser = caravel_subparsers.add_parser("run-openlane", help="Run OpenLane")
        run_openlane_parser.add_argument("caravel_root", help="Path to the caravel_user_project directory")
        run_openlane_parser.add_argument(
            "--target",
            default="user_project_wrapper",
            help="Target to build (default: user_project_wrapper)"
        )
        run_openlane_parser.set_defaults(func=caravel_run_openlane_command)

    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main() 