#!/usr/bin/env python3
import sys
import os
import json
import urllib.request
import yaml
import logging
import requests
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DEFAULT_IPS_URL: str = "https://raw.githubusercontent.com/shalan/cuprj-cli/refs/heads/main/ip-lib.json"


@dataclass
class ExternalInterface:
    """Represents an external interface for an IP slave.

    Attributes:
        name (str): The name of the interface.
        port (str): The port name.
        direction (str): The direction ("input" or "output").
        width (int): Bit width.
        description (Optional[str]): Optional description.
        output_control (bool): If True, connect the slave interface directly to io_oen.
    """
    name: str
    port: str
    direction: str
    width: int
    description: Optional[str] = None
    output_control: bool = False


@dataclass
class IPInfo:
    """Represents basic information about an IP.

    Attributes:
        name (str): The name of the IP.
        description (str): Description of the IP.
        bus (List[str]): Supported bus types.
        cell_count (List[Dict[str, Union[str, int]]]): List of cell count entries.
    """
    name: str
    description: str = "No description provided."
    bus: List[str] = field(default_factory=list)
    cell_count: List[Dict[str, Union[str, int]]] = field(default_factory=list)


@dataclass
class IPLibraryEntry:
    """Represents one IP library entry.

    Attributes:
        info (IPInfo): Basic IP information.
        external_interface (List[ExternalInterface]): External interfaces.
        flags (Optional[List[Dict[str, Any]]]): Flags for interrupt support.
        fifos (Optional[List[Dict[str, Any]]]): FIFO definitions if available.
    """
    info: IPInfo
    external_interface: List[ExternalInterface] = field(default_factory=list)
    flags: Optional[List[Dict[str, Any]]] = None
    fifos: Optional[List[Dict[str, Any]]] = None


@dataclass
class IPLibrary:
    """Represents the entire IP library.

    Attributes:
        slaves (List[IPLibraryEntry]): List of library entries.
    """
    slaves: List[IPLibraryEntry] = field(default_factory=list)

    @property
    def ip_dict(self) -> Dict[str, IPLibraryEntry]:
        """Returns a dictionary mapping IP names to their entries."""
        return {entry.info.name: entry for entry in self.slaves}


@dataclass
class BusSlave:
    """Represents a bus slave defined in the YAML configuration.

    Attributes:
        name (str): The slave name.
        type (str): The IP type.
        base_address (Optional[str]): Base address.
        io_pins (Dict[str, Union[int, str]]): Mapping of external interface names to IO pin numbers.
        irq (Optional[int]): Optional IRQ number.
    """
    name: str
    type: str
    base_address: Optional[str] = None
    io_pins: Dict[str, Union[int, str]] = field(default_factory=dict)
    irq: Optional[int] = None

    def convert_io_pins(self) -> Dict[str, int]:
        """Converts all io_pins values to integers.

        Returns:
            Dict[str, int]: The io_pins mapping with integer values.
        """
        try:
            return {k: int(v) for k, v in self.io_pins.items()}
        except Exception as e:
            logging.error(f"Error converting io_pins for slave {self.name}: {e}")
            sys.exit(1)


@dataclass
class BusSlaves:
    """Represents the bus slaves configuration.

    Attributes:
        slaves (List[BusSlave]): List of bus slaves.
    """
    slaves: List[BusSlave] = field(default_factory=list)


@dataclass
class ProcessedSlave:
    """Holds processed slave data for code generation.

    Attributes:
        name (str): Slave name.
        type (str): IP type.
        base_address (str): Base address.
        io_pins (Dict[str, int]): IO pin mappings.
        irq (Optional[int]): IRQ number.
        cell_count (int): WB cell count.
        external_interface (List[ExternalInterface]): External interfaces.
    """
    name: str
    type: str
    base_address: str
    io_pins: Dict[str, int]
    irq: Optional[int]
    cell_count: int
    external_interface: List[ExternalInterface]


def load_json_file(source: str) -> Dict[str, Any]:
    """Loads JSON data from a file or URL.

    Args:
        source (str): File path or URL.

    Returns:
        Dict[str, Any]: Parsed JSON data.
    """
    if os.path.exists(source):
        try:
            with open(source, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error reading local JSON file '{source}': {e}")
            sys.exit(1)
    else:
        try:
            with urllib.request.urlopen(source) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            logging.error(f"Error fetching JSON file '{source}': {e}")
            sys.exit(1)


def load_yaml_file(filename: str) -> Dict[str, Any]:
    """Loads YAML data from a file.

    Args:
        filename (str): Path to the YAML file.

    Returns:
        Dict[str, Any]: Parsed YAML data.
    """
    try:
        with open(filename, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Error reading YAML file '{filename}': {e}")
        sys.exit(1)


def parse_ip_library(data: Dict[str, Any]) -> IPLibrary:
    """Parses raw JSON data into an IPLibrary.

    Args:
        data (Dict[str, Any]): Raw JSON data.

    Returns:
        IPLibrary: Parsed IP library.
    """
    try:
        entries = []
        allowed_keys = {"name", "port", "direction", "width", "description", "output_control"}
        for entry in data.get("slaves", []):
            info_data = entry.get("info", {})
            ext_if_data = entry.get("external_interface", [])
            info = IPInfo(
                name=info_data.get("name", ""),
                description=info_data.get("description", "No description provided."),
                bus=info_data.get("bus", []),
                cell_count=info_data.get("cell_count", [])
            )
            flags = entry.get("flags")
            fifos = entry.get("fifos")
            interfaces = [ExternalInterface(**{k: v for k, v in iface.items() if k in allowed_keys})
                          for iface in ext_if_data]
            entries.append(IPLibraryEntry(info=info, external_interface=interfaces, flags=flags, fifos=fifos))
        return IPLibrary(slaves=entries)
    except Exception as e:
        logging.error(f"Error parsing IP library: {e}")
        sys.exit(1)


def parse_bus_slaves(data: Dict[str, Any]) -> BusSlaves:
    """Parses raw YAML data into BusSlaves.

    Args:
        data (Dict[str, Any]): Raw YAML data.

    Returns:
        BusSlaves: Parsed bus slave configuration.
    """
    try:
        slaves = [BusSlave(**slave) for slave in data.get("slaves", [])]
        return BusSlaves(slaves=slaves)
    except Exception as e:
        logging.error(f"Error parsing bus YAML: {e}")
        sys.exit(1)


class BusGenerator:
    """Generates Verilog code for the Wishbone bus module."""

    def __init__(self, bus_slaves: BusSlaves, ip_library: IPLibrary) -> None:
        """
        Args:
            bus_slaves (BusSlaves): Parsed bus slaves configuration.
            ip_library (IPLibrary): Parsed IP library.
        """
        self.bus_slaves = bus_slaves.slaves
        self.ip_library = ip_library
        self.processed_slaves: List[ProcessedSlave] = []
        self._process_slaves()

    def _process_slaves(self) -> None:
        base_addr_start = 0x10000000
        base_addr_offset = 0x10000
        ip_dict = self.ip_library.ip_dict
        for idx, slave in enumerate(self.bus_slaves):
            if slave.type not in ip_dict:
                logging.error(f"Slave type '{slave.type}' for slave '{slave.name}' not found in IP library.")
                sys.exit(1)
            lib_entry = ip_dict[slave.type]
            info = lib_entry.info
            if not any(b.upper() in {"WB", "GENERIC"} for b in info.bus):
                logging.warning(f"IP '{slave.type}' (for slave '{slave.name}') does not support WB (bus: {info.bus}). Using 0 cell count.")
                cell_count = 0
            else:
                cell_count = 0
                for entry in info.cell_count:
                    if "WB" in entry:
                        try:
                            cell_count = int(entry["WB"]) if str(entry["WB"]).isdigit() else 0
                        except Exception:
                            cell_count = 0
                        break
            if slave.irq is not None and lib_entry.flags is None:
                logging.error(f"Slave '{slave.name}' of type '{slave.type}' specifies IRQ but library entry lacks 'flags'.")
                sys.exit(1)
            base_address = slave.base_address or f"32'h{hex(base_addr_start + idx * base_addr_offset)[2:].upper()}"
            io_pins_converted = slave.convert_io_pins()
            processed = ProcessedSlave(
                name=slave.name,
                type=slave.type,
                base_address=base_address,
                io_pins=io_pins_converted,
                irq=slave.irq,
                cell_count=cell_count,
                external_interface=lib_entry.external_interface
            )
            self.processed_slaves.append(processed)

    def generate_verilog(self) -> str:
        total_wb_cell_count = sum(slave.cell_count for slave in self.processed_slaves)
        io_oen_assignments: Dict[int, int] = {}
        lines: List[str] = []
        lines.append("// Generated Wishbone Bus Verilog Code with Bus Splitter, External Interface Mapping, IRQ Checkers, and Total WB Cell Count")
        lines.append("")
        lines.append("module wb_bus(")
        lines.append("    input         wb_clk,")
        lines.append("    input         wb_rst,")
        lines.append("    input  [31:0] wb_adr,")
        lines.append("    inout  [31:0] wb_dat_i,")
        lines.append("    input         wb_we,")
        lines.append("    input         wb_stb,")
        lines.append("    input         wb_cyc,")
        lines.append("    input  [31:0] wb_dat_o,")
        lines.append("    output        wb_ack,")
        lines.append("    input  [37:0] io_in,")
        lines.append("    output [37:0] io_out,")
        lines.append("    output [37:0] io_oen,")
        lines.append("    output [2:0]  user_irq")
        lines.append(");")
        lines.append("")
        lines.append("    localparam SLAVE_ADDR_SIZE = 32'h0001_0000;")
        lines.append(f"    localparam TOTAL_WB_CELL_COUNT = {total_wb_cell_count};")
        lines.append("")
        for idx, slave in enumerate(self.processed_slaves):
            lines.append(f"    // Wires for slave {idx}: {slave.name}")
            lines.append(f"    wire [31:0] slave{idx}_dat;")
            lines.append(f"    wire        slave{idx}_ack;")
            lines.append(f"    wire        cs{idx};")
            lines.append("")
        for idx, slave in enumerate(self.processed_slaves):
            lines.append(f"    assign cs{idx} = ((wb_adr >= {slave.base_address}) && (wb_adr < ({slave.base_address} + SLAVE_ADDR_SIZE))) ? 1'b1 : 1'b0;")
        lines.append("")
        for idx, slave in enumerate(self.processed_slaves):
            lines.append(f"    // Instantiate slave {slave.name} of type {slave.type}_WB")
            inst_lines: List[str] = []
            inst_lines.append(f".clk_i(wb_clk)")
            inst_lines.append(f".rst_i(wb_rst)")
            inst_lines.append(f".adr_i(wb_adr)")
            inst_lines.append(f".dat_o(slave{idx}_dat)")
            inst_lines.append(f".dat_i(wb_dat_i)")
            inst_lines.append(f".we_i(wb_we)")
            inst_lines.append(f".stb_i(wb_stb & cs{idx})")
            inst_lines.append(f".cyc_i(wb_cyc & cs{idx})")
            inst_lines.append(f".ack_o(slave{idx}_ack)")
            # Connect external interfaces based on width and output_control property.
            for iface in slave.external_interface:
                iface_name: str = iface.name
                port_name: str = iface.port
                direction: str = iface.direction.lower()
                if iface_name not in slave.io_pins:
                    logging.error(f"Slave '{slave.name}' requires external interface '{iface_name}' but no mapping provided in io_pins.")
                    sys.exit(1)
                try:
                    pin_start: int = int(slave.io_pins[iface_name])
                except ValueError:
                    logging.error(f"I/O pin for interface '{iface_name}' in slave '{slave.name}' must be an integer.")
                    sys.exit(1)
                pin_end: int = pin_start + iface.width - 1
                if not all(0 <= p <= 37 for p in range(pin_start, pin_end + 1)):
                    logging.error(f"I/O pins from {pin_start} to {pin_end} for interface '{iface_name}' in slave '{slave.name}' are out of range (0-37).")
                    sys.exit(1)
                if direction == "input":
                    inst_lines.append(f".{port_name}(io_in[{pin_end}:{pin_start}])")
                    for p in range(pin_start, pin_end + 1):
                        io_oen_assignments.setdefault(p, 0)
                elif direction == "output":
                    if iface.output_control is True:
                        inst_lines.append(f".{port_name}(io_oen[{pin_end}:{pin_start}])")
                        for p in range(pin_start, pin_end + 1):
                            io_oen_assignments[p]= 2
                    else:
                        inst_lines.append(f".{port_name}(io_out[{pin_end}:{pin_start}])")
                        for p in range(pin_start, pin_end + 1):
                            io_oen_assignments.setdefault(p, 1)
                else:
                    logging.error(f"Unknown direction '{direction}' for interface '{iface_name}' in slave '{slave.name}'.")
                    sys.exit(1)
            if slave.irq is not None:
                if not (0 <= slave.irq <= 2):
                    logging.error(f"IRQ {slave.irq} for slave '{slave.name}' out of range (0-2).")
                    sys.exit(1)
                inst_lines.append(f".IRQ(user_irq[{slave.irq}])")

            lines.append(f"    {slave.type}_WB {slave.name} (")
            lines.append("        " + ",\n        ".join(inst_lines))
            lines.append("    );")
            lines.append("")
        lines.append("    // Bus splitter: Multiplexer for slave outputs")
        lines.append("    reg [31:0] selected_dat;")
        lines.append("    reg        selected_ack;")
        lines.append("    always @(*) begin")
        for idx in range(len(self.processed_slaves)):
            if idx == 0:
                lines.append(f"        if (cs{idx}) begin")
            else:
                lines.append(f"        else if (cs{idx}) begin")
            lines.append(f"            selected_dat = slave{idx}_dat;")
            lines.append(f"            selected_ack = slave{idx}_ack;")
            lines.append("        end")
        lines.append("        else begin")
        lines.append("            selected_dat = 32'h0;")
        lines.append("            selected_ack = 1'b0;")
        lines.append("        end")
        lines.append("    end")
        lines.append("")
        lines.append("    assign wb_dat_o = selected_dat;")
        lines.append("    assign wb_ack = selected_ack;")
        lines.append("")
        # Only assign default values to io_oen and io_out if the pin is not connected by an external interface.
        for pin in range(0, 38):
            if pin not in io_oen_assignments:
                lines.append(f"    assign io_oen[{pin}] = 1'b1;")
                lines.append(f"    assign io_out[{pin}] = 1'b0;")
            elif io_oen_assignments[pin] == 0:
                lines.append(f"    assign io_oen[{pin}] = 1'b0;")
            elif io_oen_assignments[pin] == 1:
                lines.append(f"    assign io_oen[{pin}] = 1'b1;")
        lines.append("")
        lines.append("endmodule")
        return "\n".join(lines)


def generate_wrapper(wb_bus_code: str) -> str:
    """Generates the top-level wrapper module 'user_project_wrapper'.

    Args:
        wb_bus_code (str): The Verilog code for the wb_bus module.

    Returns:
        str: The complete Verilog code with the wrapper.
    """
    lines: List[str] = []
    lines.append(wb_bus_code)
    lines.append("")
    lines.append("module user_project_wrapper #(")
    lines.append("    parameter BITS = 32")
    lines.append(") (")
    lines.append("`ifdef USE_POWER_PINS")
    lines.append("    inout vdda1,")
    lines.append("    inout vdda2,")
    lines.append("    inout vssa1,")
    lines.append("    inout vssa2,")
    lines.append("    inout vccd1,")
    lines.append("    inout vccd2,")
    lines.append("    inout vssd1,")
    lines.append("    inout vssd2,")
    lines.append("`endif")
    lines.append("    input wb_clk_i,")
    lines.append("    input wb_rst_i,")
    lines.append("    input wbs_stb_i,")
    lines.append("    input wbs_cyc_i,")
    lines.append("    input wbs_we_i,")
    lines.append("    input [3:0] wbs_sel_i,")
    lines.append("    input [31:0] wbs_dat_i,")
    lines.append("    input [31:0] wbs_adr_i,")
    lines.append("    output wbs_ack_o,")
    lines.append("    output [31:0] wbs_dat_o,")
    lines.append("    input  [127:0] la_data_in,")
    lines.append("    output [127:0] la_data_out,")
    lines.append("    input  [127:0] la_oenb,")
    lines.append("    input  [`MPRJ_IO_PADS-1:0] io_in,")
    lines.append("    output [`MPRJ_IO_PADS-1:0] io_out,")
    lines.append("    output [`MPRJ_IO_PADS-1:0] io_oeb,")
    lines.append("    inout [`MPRJ_IO_PADS-10:0] analog_io,")
    lines.append("    input   user_clock2,")
    lines.append("    output [2:0] user_irq")
    lines.append(");")
    lines.append("    wire [31:0] wb_dat_bus;")
    lines.append("    wire [`MPRJ_IO_PADS-1:0] internal_io_oen;")
    lines.append("    wb_bus u_wb_bus (")
    lines.append("        .wb_clk(wb_clk_i),")
    lines.append("        .wb_rst(wb_rst_i),")
    lines.append("        .wb_adr(wbs_adr_i),")
    lines.append("        .wb_dat_o(wbs_dat_o),")
    lines.append("        .wb_dat_i(wbs_dat_i),")
    lines.append("        .wb_we(wbs_we_i),")
    lines.append("        .wb_stb(wbs_stb_i),")
    lines.append("        .wb_cyc(wbs_cyc_i),")
    lines.append("        .wb_ack(wbs_ack_o),")
    lines.append("        .io_in(io_in),")
    lines.append("        .io_out(io_out),")
    lines.append("        .io_oen(internal_io_oen),")
    lines.append("        .user_irq(user_irq)")
    lines.append("    );")
    lines.append("    assign io_oeb = ~internal_io_oen;")
    lines.append("endmodule")
    return "\n".join(lines)


def convert_base_address_to_c_format(addr: str) -> str:
    """Converts a base address string from Verilog style (e.g. 32'h30000000) to C hex format (e.g. 0x30000000).

    Args:
        addr (str): The base address string.

    Returns:
        str: The converted C-style hex string.
    """
    if addr.startswith("32'h") or addr.startswith("32'H"):
        return "0x" + addr[4:]
    elif addr.startswith("0x"):
        return addr
    else:
        try:
            num = int(addr, 0)
            return hex(num)
        except Exception:
            return addr
        
def generate_c_header(generator: "BusGenerator", bus_yaml_file: str) -> str:
    """Generates a C header file string with macros defining base addresses for each slave.

    Args:
        generator (BusGenerator): The BusGenerator instance with processed slaves.
        bus_yaml_file (str): The YAML file name used, for generating the header guard.

    Returns:
        str: The C header file content.
    """
    output_header_filename = bus_yaml_file
    if output_header_filename.lower().endswith(".yaml"):
        output_header_filename = output_header_filename[:-5] + ".h"
    elif output_header_filename.lower().endswith(".yml"):
        output_header_filename = output_header_filename[:-4] + ".h"
    else:
        output_header_filename += ".h"
    header_guard = "__" + os.path.basename(output_header_filename).replace(".", "_").upper() + "__"
    lines: List[str] = []
    lines.append(f"#ifndef {header_guard}")
    lines.append(f"#define {header_guard}")
    lines.append("")
    for slave in generator.processed_slaves:
        macro_name = slave.name.upper() + "_BASE"
        base_addr_c = convert_base_address_to_c_format(slave.base_address)
        lines.append(f"#define {macro_name} {base_addr_c}")
    lines.append("")
    lines.append(f"#endif // {header_guard}")
    return "\n".join(lines)


def parse_repo_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extracts the 'owner' and 'repo' from a GitHub URL.
    
    Args:
        url: A GitHub URL, with or without "github.com/" prefix.
             For example, both 'github.com/owner/repo' and 'owner/repo'.
    
    Returns:
        A tuple containing (owner, repo) or (None, None) if parsing fails.
    """
    url = url.strip()
    # Remove a leading "github.com/" if present
    if url.startswith("github.com/"):
        url = url[len("github.com/"):]
    parts = url.split('/')
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None, None


def fetch_yaml_from_repo(owner: str, repo: str) -> Optional[Tuple[str, str]]:
    """
    Attempts to fetch the YAML file named '<repo>.yaml' from the repository's root.
    
    Args:
        owner: The GitHub repository owner/organization.
        repo: The GitHub repository name.
    
    Returns:
        A tuple (filename, content) if successful, otherwise None.
    """
    filename = f"{repo}.yaml"
    branches = ["main", "master"]
    
    for branch in branches:
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filename}"
        response = requests.get(raw_url)
        if response.status_code == 200:
            logging.info(f"Found YAML file at: {raw_url}")
            return filename, response.text
        else:
            logging.info(f"Could not find file at {raw_url} (HTTP {response.status_code}).")
    logging.info(f"YAML file {filename} not found in repository {owner}/{repo}.")
    return None 