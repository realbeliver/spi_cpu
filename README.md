![GDS Badge](../../workflows/gds/badge.svg)
![Docs Badge](../../workflows/docs/badge.svg)
![Test Badge](../../workflows/test/badge.svg)
![FPGA Badge](../../workflows/fpga/badge.svg)

# TinyTapeout SPI Microcoded CPU

A tiny **4-bit CPU** for **TinyTapeout (GF180MCU)** that executes its program from **external SPI RAM**. In the current demo, the microcode implements a **4×4-bit to 8-bit multiplier**, where the two 4-bit operands come in through `ui_in` and the 8-bit product is driven on `uo_out` [page:27].

- `ui_in[7:4] = A`
- `ui_in[3:0] = B`
- `uo_out[7:0] = A × B`

More design details are documented in [docs/info.md](docs/info.md).

## Project Summary

This project is a small microcoded CPU intended for TinyTapeout-style experimentation with simple datapaths, external program storage, and instruction sequencing over SPI [page:27]. The goal is to keep the design readable and hackable while still being realistic enough for silicon bring-up and external-memory-based execution [page:27].

The CPU does not store its program internally. Instead, instruction bytes are fetched from an SPI memory device, which can be emulated using an RP2040 or another microcontroller that behaves like a simple 23LC512-style RAM [page:27].

## Architecture

The design is split into three main blocks:

1. **TinyTapeout wrapper**: `tt_um_spi_cpu_top`
2. **CPU wrapper + SPI fetch logic**: `spi_wrap`
3. **Execution datapath**: `ExecutionUnit`

### 1. TinyTapeout wrapper

The top-level module connects the TinyTapeout pins to the internal CPU and SPI interface. It accepts the two 4-bit input operands on `ui_in`, returns the 8-bit result on `uo_out`, and exposes SPI-related signals through the `uio_*` pins [page:27].

### 2. SPI fetch wrapper

`spi_wrap` contains:
- the program counter,
- a small FSM for instruction fetch,
- the byte-oriented SPI read engine,
- and the interface to the execution unit.

Each byte fetched over SPI contains **two 4-bit micro-operations**. The lower nibble is executed first, followed by the upper nibble, then the program counter advances to the next byte [page:27].

### 3. ExecutionUnit datapath

The execution unit contains:
- A, B, and O registers,
- an 8-bit accumulator,
- a shift register with flag,
- an ALU,
- and control/decode logic.

The instruction set is intentionally compact and is built around simple load, shift, arithmetic, and logical operations that are enough to implement multiplication in microcode [page:27].

## Pin Mapping

| Signal | Pin | Direction | Description |
|--------|-----|-----------|-------------|
| `ui_in[7:4]` | `ui_in[7:4]` | Input | 4-bit operand A |
| `ui_in[3:0]` | `ui_in[3:0]` | Input | 4-bit operand B 
