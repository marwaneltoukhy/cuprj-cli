"""
Caravel User's Project CLI - A tool for generating Verilog code for Wishbone systems.
"""

__version__ = "0.1.0"

from .core import (
    IPInfo,
    ExternalInterface,
    IPLibraryEntry,
    IPLibrary,
    BusSlave,
    BusSlaves,
    ProcessedSlave,
    BusGenerator,
    parse_ip_library,
    load_json_file,
    load_yaml_file,
    parse_bus_slaves,
    generate_wrapper,
    generate_c_header,
) 