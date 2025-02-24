// Generated Wishbone Bus Verilog Code with Bus Splitter, External Interface Mapping, IRQ Checkers, and Total WB Cell Count

module wb_bus(
    input         wb_clk,
    input         wb_rst,
    input  [31:0] wb_adr,
    inout  [31:0] wb_dat_i,
    input         wb_we,
    input         wb_stb,
    input         wb_cyc,
    input  [31:0] wb_dat_o,
    output        wb_ack,
    input  [37:0] io_in,
    output [37:0] io_out,
    output [37:0] io_oen,
    output [2:0]  user_irq
);

    localparam SLAVE_ADDR_SIZE = 32'h0001_0000;
    localparam TOTAL_WB_CELL_COUNT = 2170;

    // Wires for slave 0: EF_UART_0
    wire [31:0] slave0_dat;
    wire        slave0_ack;
    wire        cs0;

    // Wires for slave 1: EF_SHA256_1
    wire [31:0] slave1_dat;
    wire        slave1_ack;
    wire        cs1;

    // Wires for slave 2: EF_I2C_2
    wire [31:0] slave2_dat;
    wire        slave2_ack;
    wire        cs2;

    assign cs0 = ((wb_adr >= 32'h30000000) && (wb_adr < (32'h30000000 + SLAVE_ADDR_SIZE))) ? 1'b1 : 1'b0;
    assign cs1 = ((wb_adr >= 32'h30010000) && (wb_adr < (32'h30010000 + SLAVE_ADDR_SIZE))) ? 1'b1 : 1'b0;
    assign cs2 = ((wb_adr >= 32'h30020000) && (wb_adr < (32'h30020000 + SLAVE_ADDR_SIZE))) ? 1'b1 : 1'b0;

    // Instantiate slave EF_UART_0 of type EF_UART_WB
    EF_UART_WB EF_UART_0 (
        .clk_i(wb_clk),
        .rst_i(wb_rst),
        .adr_i(wb_adr),
        .dat_o(slave0_dat),
        .dat_i(wb_dat_i),
        .we_i(wb_we),
        .stb_i(wb_stb & cs0),
        .cyc_i(wb_cyc & cs0),
        .ack_o(slave0_ack),
        .rx(io_in[10:10]),
        .tx(io_out[10:10]),
        .IRQ(user_irq[0])
    );

    // Instantiate slave EF_SHA256_1 of type EF_SHA256_WB
    EF_SHA256_WB EF_SHA256_1 (
        .clk_i(wb_clk),
        .rst_i(wb_rst),
        .adr_i(wb_adr),
        .dat_o(slave1_dat),
        .dat_i(wb_dat_i),
        .we_i(wb_we),
        .stb_i(wb_stb & cs1),
        .cyc_i(wb_cyc & cs1),
        .ack_o(slave1_ack),
        .IRQ(user_irq[1])
    );

    // Instantiate slave EF_I2C_2 of type EF_I2C_WB
    EF_I2C_WB EF_I2C_2 (
        .clk_i(wb_clk),
        .rst_i(wb_rst),
        .adr_i(wb_adr),
        .dat_o(slave2_dat),
        .dat_i(wb_dat_i),
        .we_i(wb_we),
        .stb_i(wb_stb & cs2),
        .cyc_i(wb_cyc & cs2),
        .ack_o(slave2_ack),
        .scl_i(io_in[12:12]),
        .scl_o(io_out[12:12]),
        .scl_oen_o(io_oen[12:12]),
        .sda_i(io_in[12:12]),
        .sda_o(io_out[12:12]),
        .sda_oen_o(io_out[12:12]),
        .i2c_irq(io_out[12:12]),
        .IRQ(user_irq[2])
    );

    // Bus splitter: Multiplexer for slave outputs
    reg [31:0] selected_dat;
    reg        selected_ack;
    always @(*) begin
        if (cs0) begin
            selected_dat = slave0_dat;
            selected_ack = slave0_ack;
        end
        else if (cs1) begin
            selected_dat = slave1_dat;
            selected_ack = slave1_ack;
        end
        else if (cs2) begin
            selected_dat = slave2_dat;
            selected_ack = slave2_ack;
        end
        else begin
            selected_dat = 32'h0;
            selected_ack = 1'b0;
        end
    end

    assign wb_dat_o = selected_dat;
    assign wb_ack = selected_ack;

    assign io_oen[0] = 1'b1;
    assign io_out[0] = 1'b0;
    assign io_oen[1] = 1'b1;
    assign io_out[1] = 1'b0;
    assign io_oen[2] = 1'b1;
    assign io_out[2] = 1'b0;
    assign io_oen[3] = 1'b1;
    assign io_out[3] = 1'b0;
    assign io_oen[4] = 1'b1;
    assign io_out[4] = 1'b0;
    assign io_oen[5] = 1'b1;
    assign io_out[5] = 1'b0;
    assign io_oen[6] = 1'b1;
    assign io_out[6] = 1'b0;
    assign io_oen[7] = 1'b1;
    assign io_out[7] = 1'b0;
    assign io_oen[8] = 1'b1;
    assign io_out[8] = 1'b0;
    assign io_oen[9] = 1'b1;
    assign io_out[9] = 1'b0;
    assign io_oen[10] = 1'b0;
    assign io_oen[11] = 1'b1;
    assign io_out[11] = 1'b0;
    assign io_oen[13] = 1'b1;
    assign io_out[13] = 1'b0;
    assign io_oen[14] = 1'b1;
    assign io_out[14] = 1'b0;
    assign io_oen[15] = 1'b1;
    assign io_out[15] = 1'b0;
    assign io_oen[16] = 1'b1;
    assign io_out[16] = 1'b0;
    assign io_oen[17] = 1'b1;
    assign io_out[17] = 1'b0;
    assign io_oen[18] = 1'b1;
    assign io_out[18] = 1'b0;
    assign io_oen[19] = 1'b1;
    assign io_out[19] = 1'b0;
    assign io_oen[20] = 1'b1;
    assign io_out[20] = 1'b0;
    assign io_oen[21] = 1'b1;
    assign io_out[21] = 1'b0;
    assign io_oen[22] = 1'b1;
    assign io_out[22] = 1'b0;
    assign io_oen[23] = 1'b1;
    assign io_out[23] = 1'b0;
    assign io_oen[24] = 1'b1;
    assign io_out[24] = 1'b0;
    assign io_oen[25] = 1'b1;
    assign io_out[25] = 1'b0;
    assign io_oen[26] = 1'b1;
    assign io_out[26] = 1'b0;
    assign io_oen[27] = 1'b1;
    assign io_out[27] = 1'b0;
    assign io_oen[28] = 1'b1;
    assign io_out[28] = 1'b0;
    assign io_oen[29] = 1'b1;
    assign io_out[29] = 1'b0;
    assign io_oen[30] = 1'b1;
    assign io_out[30] = 1'b0;
    assign io_oen[31] = 1'b1;
    assign io_out[31] = 1'b0;
    assign io_oen[32] = 1'b1;
    assign io_out[32] = 1'b0;
    assign io_oen[33] = 1'b1;
    assign io_out[33] = 1'b0;
    assign io_oen[34] = 1'b1;
    assign io_out[34] = 1'b0;
    assign io_oen[35] = 1'b1;
    assign io_out[35] = 1'b0;
    assign io_oen[36] = 1'b1;
    assign io_out[36] = 1'b0;
    assign io_oen[37] = 1'b1;
    assign io_out[37] = 1'b0;

endmodule