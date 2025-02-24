#!/usr/bin/env python3
import os
import sys
import re
import json
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

class CaravelIntegration:
    """Handles integration with Caravel User Project structure."""
    
    def __init__(self, caravel_root: str):
        """Initialize with the root directory of the caravel_user_project.
        
        Args:
            caravel_root: Path to the caravel_user_project directory
        """
        self.caravel_root = Path(caravel_root)
        self.verilog_rtl_dir = self.caravel_root / "verilog" / "rtl"
        self.openlane_dir = self.caravel_root / "openlane"
        self.cocotb_dir = self.caravel_root / "verilog" / "dv"
        
        # Verify the directory structure
        self._verify_caravel_structure()
    
    def _verify_caravel_structure(self) -> None:
        """Verify that the provided directory has the expected Caravel structure."""
        required_dirs = [
            self.verilog_rtl_dir,
            self.openlane_dir,
            self.openlane_dir / "user_project_wrapper",
            self.cocotb_dir
        ]
        
        for directory in required_dirs:
            if not directory.exists() or not directory.is_dir():
                logging.error(f"Required directory not found: {directory}")
                logging.error("This does not appear to be a valid caravel_user_project directory.")
                sys.exit(1)
        
        # Check for user_project_wrapper.v file
        if not (self.verilog_rtl_dir / "user_project_wrapper.v").exists():
            logging.error(f"user_project_wrapper.v not found in {self.verilog_rtl_dir}")
            sys.exit(1)
        
        # Check for OpenLane config file (either config.tcl or config.json)
        config_tcl = self.openlane_dir / "user_project_wrapper" / "config.tcl"
        config_json = self.openlane_dir / "user_project_wrapper" / "config.json"
        
        if not config_tcl.exists() and not config_json.exists():
            logging.error(f"Neither config.tcl nor config.json found in {self.openlane_dir / 'user_project_wrapper'}")
            sys.exit(1)
    
    def update_user_project_wrapper(self, verilog_code: str) -> None:
        """Update the user_project_wrapper.v file with the generated Verilog code.
        
        Args:
            verilog_code: The generated Verilog code to write
        """
        wrapper_file = self.verilog_rtl_dir / "user_project_wrapper.v"
        
        # Backup the original file
        backup_file = wrapper_file.with_suffix(".v.bak")
        shutil.copy2(wrapper_file, backup_file)
        logging.info(f"Backed up original user_project_wrapper.v to {backup_file}")
        
        # Read the original file
        with open(wrapper_file, "r") as f:
            original_content = f.read()
        
        # First, look for the user_proj_example instantiation
        user_proj_pattern = r'(user_proj_example\s+mprj\s*\([^;]*;)'
        user_proj_match = re.search(user_proj_pattern, original_content, re.DOTALL)
        
        if user_proj_match:
            # Found the user_proj_example instantiation
            user_project_section = user_proj_match.group(1)
            
            # Create the new instantiation
            new_instantiation = '''// Instantiate the wb_bus module
wire [`MPRJ_IO_PADS-1:0] internal_io_oen;

wb_bus u_wb_bus (
    .wb_clk(wb_clk_i),
    .wb_rst(wb_rst_i),
    .wb_adr(wbs_adr_i),
    .wb_dat_o(wbs_dat_o),
    .wb_dat_i(wbs_dat_i),
    .wb_we(wbs_we_i),
    .wb_stb(wbs_stb_i),
    .wb_cyc(wbs_cyc_i),
    .wb_ack(wbs_ack_o),
    .io_in(io_in),
    .io_out(io_out),
    .io_oen(internal_io_oen),
    .user_irq(user_irq)
);

// Convert io_oen to io_oeb (active low to active high)
assign io_oeb = ~internal_io_oen;'''
            
            # Replace the user project instantiation section
            new_content = original_content.replace(user_project_section, new_instantiation)
            
            # Write the new file
            with open(wrapper_file, "w") as f:
                f.write(new_content)
            
            logging.info(f"Updated {wrapper_file}")
            return
        
        # If we couldn't find the user_proj_example instantiation, try other patterns
        patterns = [
            r'(/\*-*\s*\*/\s*/\*\s*User project is instantiated here\s*\*/\s*/\*-*\s*\*/\s*)(.*?)(\s*endmodule)',
            r'(/\*.*?User project.*?instantiated.*?\*/\s*)(.*?)(\s*endmodule)',
            r'(/\*.*?User project.*?\*/\s*)(.*?)(\s*endmodule)'
        ]
        
        for pattern in patterns:
            user_project_match = re.search(pattern, original_content, re.DOTALL)
            if user_project_match:
                # Get the comment section and the endmodule part
                comment_section = user_project_match.group(1)
                endmodule_part = user_project_match.group(3)
                
                # Create the new instantiation
                new_instantiation = comment_section + '''
// Instantiate the wb_bus module
wire [`MPRJ_IO_PADS-1:0] internal_io_oen;

wb_bus u_wb_bus (
    .wb_clk(wb_clk_i),
    .wb_rst(wb_rst_i),
    .wb_adr(wbs_adr_i),
    .wb_dat_o(wbs_dat_o),
    .wb_dat_i(wbs_dat_i),
    .wb_we(wbs_we_i),
    .wb_stb(wbs_stb_i),
    .wb_cyc(wbs_cyc_i),
    .wb_ack(wbs_ack_o),
    .io_in(io_in),
    .io_out(io_out),
    .io_oen(internal_io_oen),
    .user_irq(user_irq)
);

// Convert io_oen to io_oeb (active low to active high)
assign io_oeb = ~internal_io_oen;''' + endmodule_part
                
                # Replace the user project instantiation section
                new_content = re.sub(pattern, new_instantiation, original_content, flags=re.DOTALL)
                
                # Write the new file
                with open(wrapper_file, "w") as f:
                    f.write(new_content)
                
                logging.info(f"Updated {wrapper_file}")
                return
        
        # If we still couldn't find the user project instantiation section, try a more direct approach
        # Look for the section between the last input/output declaration and the endmodule
        io_section_end = re.search(r'output\s+\[2:0\]\s+user_irq[^;]*;', original_content)
        if io_section_end:
            io_end_pos = io_section_end.end()
            before_content = original_content[:io_end_pos]
            after_content = original_content[io_end_pos:]
            
            # Find the endmodule statement
            endmodule_match = re.search(r'\s*endmodule', after_content)
            if endmodule_match:
                endmodule_pos = endmodule_match.start()
                after_endmodule = after_content[endmodule_pos:]
                
                # Create the new content
                new_content = before_content + "\n\n" + '''/*--------------------------------------*/
/* User project is instantiated here    */
/*--------------------------------------*/

// Instantiate the wb_bus module
wire [`MPRJ_IO_PADS-1:0] internal_io_oen;

wb_bus u_wb_bus (
    .wb_clk(wb_clk_i),
    .wb_rst(wb_rst_i),
    .wb_adr(wbs_adr_i),
    .wb_dat_o(wbs_dat_o),
    .wb_dat_i(wbs_dat_i),
    .wb_we(wbs_we_i),
    .wb_stb(wbs_stb_i),
    .wb_cyc(wbs_cyc_i),
    .wb_ack(wbs_ack_o),
    .io_in(io_in),
    .io_out(io_out),
    .io_oen(internal_io_oen),
    .user_irq(user_irq)
);

// Convert io_oen to io_oeb (active low to active high)
assign io_oeb = ~internal_io_oen;''' + after_endmodule
                
                # Write the new file
                with open(wrapper_file, "w") as f:
                    f.write(new_content)
                
                logging.info(f"Updated {wrapper_file}")
                return
        
        # If all else fails, log an error with helpful information
        logging.error("Could not find user project instantiation section in the original file")
        logging.error("Please check the format of your user_project_wrapper.v file")
        logging.error("File content snippet:")
        logging.error(original_content[:500] + "...")
        sys.exit(1)
    
    def update_openlane_config(self, module_names: List[str], cell_counts: Dict[str, int]) -> None:
        """Update the OpenLane config file with the new module information.
        
        Args:
            module_names: List of module names to include
            cell_counts: Dictionary mapping module names to their cell counts
        """
        # Check if we have config.tcl or config.json
        config_tcl = self.openlane_dir / "user_project_wrapper" / "config.tcl"
        config_json = self.openlane_dir / "user_project_wrapper" / "config.json"
        
        if config_tcl.exists():
            self._update_openlane_config_tcl(config_tcl, module_names, cell_counts)
        elif config_json.exists():
            self._update_openlane_config_json(config_json, module_names, cell_counts)
        else:
            logging.error("No OpenLane configuration file found.")
            sys.exit(1)
    
    def _update_openlane_config_tcl(self, config_file: Path, module_names: List[str], cell_counts: Dict[str, int]) -> None:
        """Update the OpenLane config.tcl file with the new module information.
        
        Args:
            config_file: Path to the config.tcl file
            module_names: List of module names to include
            cell_counts: Dictionary mapping module names to their cell counts
        """
        # Backup the original file
        backup_file = config_file.with_suffix(".tcl.bak")
        shutil.copy2(config_file, backup_file)
        logging.info(f"Backed up original config.tcl to {backup_file}")
        
        # Read the original file
        with open(config_file, "r") as f:
            config_content = f.read()
        
        # Update VERILOG_FILES_BLACKBOX
        verilog_files_pattern = r'set ::env\(VERILOG_FILES_BLACKBOX\)\s+"([^"]+)"'
        verilog_files_match = re.search(verilog_files_pattern, config_content)
        
        if verilog_files_match:
            original_value = verilog_files_match.group(1)
            # Add new module files
            module_files = " ".join([f"$::env(DESIGN_DIR)/../../verilog/rtl/{module}_WB.v" for module in module_names])
            new_value = f"{original_value} {module_files}"
            config_content = re.sub(verilog_files_pattern, f'set ::env(VERILOG_FILES_BLACKBOX) "{new_value}"', config_content)
        
        # Write the updated config
        with open(config_file, "w") as f:
            f.write(config_content)
        
        logging.info(f"Updated OpenLane config file: {config_file}")
    
    def _update_openlane_config_json(self, config_file: Path, module_names: List[str], cell_counts: Dict[str, int]) -> None:
        """Update the OpenLane config.json file with the new module information.
        
        Args:
            config_file: Path to the config.json file
            module_names: List of module names to include
            cell_counts: Dictionary mapping module names to their cell counts
        """
        # Backup the original file
        backup_file = config_file.with_suffix(".json.bak")
        shutil.copy2(config_file, backup_file)
        logging.info(f"Backed up original config.json to {backup_file}")
        
        # Read the original file
        with open(config_file, "r") as f:
            config_data = json.load(f)
        
        # Update VERILOG_FILES_BLACKBOX if it exists
        if "VERILOG_FILES_BLACKBOX" in config_data:
            verilog_files = config_data["VERILOG_FILES_BLACKBOX"]
            if isinstance(verilog_files, str):
                verilog_files = verilog_files.split()
            
            # Add new module files if they don't already exist
            for module in module_names:
                module_file = f"$::env(DESIGN_DIR)/../../verilog/rtl/{module}_WB.v"
                if module_file not in verilog_files:
                    verilog_files.append(module_file)
            
            # Update the config
            if isinstance(config_data["VERILOG_FILES_BLACKBOX"], str):
                config_data["VERILOG_FILES_BLACKBOX"] = " ".join(verilog_files)
            else:
                config_data["VERILOG_FILES_BLACKBOX"] = verilog_files
        else:
            # Create VERILOG_FILES_BLACKBOX if it doesn't exist
            module_files = [f"$::env(DESIGN_DIR)/../../verilog/rtl/{module}_WB.v" for module in module_names]
            config_data["VERILOG_FILES_BLACKBOX"] = module_files
        
        # Write the updated config
        with open(config_file, "w") as f:
            json.dump(config_data, f, indent=2)
        
        logging.info(f"Updated OpenLane config file: {config_file}")
    
    def create_cocotb_test(self, test_name: str, module_names: List[str]) -> None:
        """Create a basic cocotb test for the generated design.
        
        Args:
            test_name: Name for the test
            module_names: List of module names to test
        """
        test_dir = self.cocotb_dir / test_name
        
        # Create test directory if it doesn't exist
        test_dir.mkdir(exist_ok=True)
        
        # Create a basic test file
        test_file = test_dir / f"{test_name}.py"
        
        # Use triple quotes with proper escaping for the docstring in the test
        modules_str = ", ".join(module_names)
        test_content = f'''
import os
import random
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer, ClockCycles

@cocotb.test()
async def test_{test_name}(dut):
    """Test the generated Wishbone bus with {modules_str}."""
    
    # Start the clock
    clock = Clock(dut.wb_clk_i, 10, units="ns")
    cocotb.start_soon(clock.start())
    
    # Reset
    dut.wb_rst_i.value = 1
    await ClockCycles(dut.wb_clk_i, 5)
    dut.wb_rst_i.value = 0
    await ClockCycles(dut.wb_clk_i, 5)
    
    # TODO: Add specific test for each module
    # Example for a simple register read/write test:
    
    # Set up a Wishbone transaction
    dut.wbs_stb_i.value = 1
    dut.wbs_cyc_i.value = 1
    dut.wbs_we_i.value = 1  # Write
    dut.wbs_sel_i.value = 0xF  # All bytes
    
    # Write to the first module
    dut.wbs_adr_i.value = 0x30000000  # Base address
    dut.wbs_dat_i.value = 0x12345678  # Test data
    
    # Wait for acknowledgement
    await RisingEdge(dut.wbs_ack_o)
    
    # End the write transaction
    dut.wbs_stb_i.value = 0
    dut.wbs_cyc_i.value = 0
    await ClockCycles(dut.wb_clk_i, 5)
    
    # Start a read transaction
    dut.wbs_stb_i.value = 1
    dut.wbs_cyc_i.value = 1
    dut.wbs_we_i.value = 0  # Read
    dut.wbs_adr_i.value = 0x30000000  # Same address
    
    # Wait for acknowledgement
    await RisingEdge(dut.wbs_ack_o)
    
    # Check the read data
    read_value = dut.wbs_dat_o.value
    assert read_value == 0x12345678, f"Read value {{read_value}} does not match expected 0x12345678"
    
    # End the read transaction
    dut.wbs_stb_i.value = 0
    dut.wbs_cyc_i.value = 0
    
    await ClockCycles(dut.wb_clk_i, 10)
'''
        
        with open(test_file, "w") as f:
            f.write(test_content)
        
        # Create a Makefile for the test
        makefile = test_dir / "Makefile"
        makefile_content = f'''
# Makefile for {test_name} cocotb test

VERILOG_SOURCES = $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v \\
                  $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v \\
                  $(CARAVEL_ROOT)/verilog/gl/user_project_wrapper.v

# Include the generated modules
VERILOG_SOURCES += $(CARAVEL_ROOT)/verilog/rtl/user_project_wrapper.v
'''
        
        for module in module_names:
            makefile_content += f"VERILOG_SOURCES += $(CARAVEL_ROOT)/verilog/rtl/{module}_WB.v\n"
        
        makefile_content += f'''
TOPLEVEL = user_project_wrapper
MODULE = {test_name}

include $(shell cocotb-config --makefiles)/Makefile.sim
'''
        
        with open(makefile, "w") as f:
            f.write(makefile_content)
        
        logging.info(f"Created cocotb test: {test_file}")
        logging.info(f"Created test Makefile: {makefile}")
    
    def run_cocotb_test(self, test_name: str, simulation_type: str = "rtl") -> bool:
        """Run a cocotb test.
        
        Args:
            test_name: Name of the test to run
            simulation_type: Type of simulation (rtl, gl, or gl-sdf)
            
        Returns:
            bool: True if the test passed, False otherwise
        """
        test_dir = self.cocotb_dir / test_name
        
        if not test_dir.exists():
            logging.error(f"Test directory not found: {test_dir}")
            return False
        
        # Set up the command
        cmd = ["make", f"verify-{test_name}-{simulation_type}"]
        
        try:
            # Run the command from the caravel root directory
            process = subprocess.Popen(
                cmd,
                cwd=self.caravel_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Stream the output
            for line in process.stdout:
                print(line, end="")
            
            # Wait for the process to complete
            process.wait()
            
            if process.returncode == 0:
                logging.info(f"Test {test_name} ({simulation_type}) passed!")
                return True
            else:
                logging.error(f"Test {test_name} ({simulation_type}) failed with return code {process.returncode}")
                return False
                
        except Exception as e:
            logging.error(f"Error running test: {e}")
            return False
    
    def run_openlane(self, target: str = "user_project_wrapper") -> bool:
        """Run OpenLane to harden the design.
        
        Args:
            target: The target to build (default: user_project_wrapper)
            
        Returns:
            bool: True if OpenLane ran successfully, False otherwise
        """
        # Set default PDK_ROOT and OPENLANE_ROOT if not already set
        env = os.environ.copy()
        
        if "PDK_ROOT" not in env:
            # Use default PDK_ROOT based on caravel_root
            default_pdk_root = os.path.join(os.path.dirname(self.caravel_root), "dependencies/pdks")
            env["PDK_ROOT"] = default_pdk_root
            logging.info(f"PDK_ROOT not set, using default: {default_pdk_root}")
        
        if "OPENLANE_ROOT" not in env:
            # Use default OPENLANE_ROOT based on caravel_root
            default_openlane_root = os.path.join(os.path.dirname(self.caravel_root), "dependencies/openlane_src")
            env["OPENLANE_ROOT"] = default_openlane_root
            logging.info(f"OPENLANE_ROOT not set, using default: {default_openlane_root}")
        
        # Log the environment variables
        logging.info(f"Using PDK_ROOT: {env['PDK_ROOT']}")
        logging.info(f"Using OPENLANE_ROOT: {env['OPENLANE_ROOT']}")
        
        # Use a simpler command that's more likely to work
        cmd = ["make", target]
        
        try:
            logging.info(f"Running OpenLane for target: {target}")
            logging.info(f"Working directory: {self.caravel_root}")
            logging.info(f"Command: {' '.join(cmd)}")
            
            # Run the command from the caravel root directory
            process = subprocess.Popen(
                cmd,
                cwd=self.caravel_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env  # Use our modified environment
            )
            
            # Stream the output
            for line in process.stdout:
                print(line, end="")
                logging.info(line.strip())
            
            # Wait for the process to complete
            process.wait()
            
            # Check for errors in stderr
            stderr_output = process.stderr.read()
            if stderr_output:
                logging.error(f"Error output from OpenLane:\n{stderr_output}")
            
            if process.returncode == 0:
                logging.info(f"OpenLane run for {target} completed successfully!")
                return True
            else:
                logging.error(f"OpenLane run for {target} failed with return code {process.returncode}")
                logging.error("Please check that you have the correct PDK and OpenLane setup.")
                logging.error("You may need to run 'make setup' in the caravel_user_project directory first.")
                return False
                
        except Exception as e:
            logging.error(f"Error running OpenLane: {e}")
            return False 