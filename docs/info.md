# Info - TinyTapeout SPI Microcoded CPU

#<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
--->

## How it works

This project implements a **single-cycle combinational floating-point multiplier** using a custom 15-bit format called **SEM15** (1 sign / 6 exponent / 8 mantissa, bias = 31), targeting the TinyTapeout GF180MCU platform.

Two signed **Q8.8 fixed-point** operands are loaded byte-serially over `ui_in`, encoded into SEM15, multiplied in floating-point, decoded back to Q8.8, and the result is available **1 clock after FIRE**. The entire multiply datapath is purely combinational with no pipeline registers, keeping the design at ~1,850 cells — fits 1×2.

### SEM15 Format

SEM15 is an original custom 15-bit float, derived from SEM20 with a reduced mantissa to meet the 1×2 tile area constraint:

| Field | Bits | Description |
|-------|------|-------------|
| Sign | `[14]` | 0 = positive, 1 = negative |
| Exponent | `[13:8]` | 6-bit biased, bias = 31 |
| Mantissa | `[7:0]` | 8-bit stored fraction, implicit leading 1 |

- Dynamic range: 2⁻³¹ to 2³¹ — same as the original SEM20 exponent field
- Precision: ~2.4 decimal digits
- Zero: `15'h0000`
- Overflow saturates to `{sign, 6'd62, 8'hFF}`
- Underflow flushes to zero. No NaN, no Inf.

### Architecture

```
  ui_in (Q8.8 bytes)
        │
   [a_reg / b_reg]      ← only FFs in the design (IO registers)
        │
  q8p8_to_sem15 ──► sem15_mul ──► sem15_to_q8p8
  (combinational)   (combinational)  (combinational)
        │
   [result_reg]         ← captures result on FIRE posedge
        │
     uo_out (Q8.8)

  Latency : 1 clock after FIRE
  Cells   : ~1,850  (fits 1x2 tile)
```

**q8p8_to_sem15** — sign + abs, 16-bit LZD (casez), biased exponent `E = MSB + 23`, normalize, pack.

**sem15_mul** — unpack, exponent sum `Ea + Eb − 31`, 9×9 unsigned mantissa multiply → 18-bit product, normalize (leading 1 at bit 16 or 17), round-to-nearest, saturate.

**sem15_to_q8p8** — unpack, barrel shift by `(E − 31)`, sign application, saturate to Q8.8 range.

### IO Protocol

Operands are 16-bit Q8.8 values, loaded as two bytes each using a CMD field on `uio_in`.

| Pin | Dir | Function |
|-----|-----|----------|
| `ui[7:0]` | IN | 8-bit data bus |
| `uo[7:0]` | OUT | Result byte |
| `uio[0]` | OUT | `out_valid` — 1-cycle pulse 1 clock after FIRE |
| `uio[3:2]` | IN | `CMD` — `00`=NOP `01`=LOAD_A `10`=LOAD_B `11`=FIRE |
| `uio[4]` | IN | `BYTE_SEL` — `0`=low byte `1`=high byte |
| `uio[6]` | IN | `RESULT_HI` — `0`=`result[7:0]` `1`=`result[15:8]` |

## How to test

Load operands A and B byte-serially, send FIRE, then read the result byte(s) on the next clock.

### Host sequence (one multiply)

```
cycle 1 : CMD=LOAD_A, BYTE_SEL=0, ui_in = a[7:0]
cycle 2 : CMD=LOAD_A, BYTE_SEL=1, ui_in = a[15:8]
cycle 3 : CMD=LOAD_B, BYTE_SEL=0, ui_in = b[7:0]
cycle 4 : CMD=LOAD_B, BYTE_SEL=1, ui_in = b[15:8]
cycle 5 : CMD=FIRE
cycle 6 : out_valid=1  →  read uo_out (RESULT_HI=0 for low byte, 1 for high byte)
```

Q8.8 encoding: `float × 256` as a signed 16-bit integer.
Examples: `1.5 → 0x0180`, `−3.0 → 0xFD00`, `0.25 → 0x0040`.

### Running the cocotb testbench

```sh
cd test
make
```

| Test | A | B | Expected |
|------|---|---|----------|
| `test_basic` | 1.0 | 2.0 | 2.0 |
| `test_fraction` | 1.5 | 2.0 | 3.0 |
| `test_negative` | −1.0 | 3.0 | −3.0 |
| `test_both_negative` | −2.0 | −3.0 | 6.0 |
| `test_saturation` | 100.0 | 100.0 | +127.996 (sat) |
| `test_zero` | 0.0 | 5.0 | 0.0 |
| `test_small_fraction` | 0.25 | 0.25 | 0.0625 |
| `test_large` | 7.5 | 3.0 | 22.5 |

## External hardware

None. The host microcontroller (e.g. RP2040 on the TT demo board) drives `ui_in` and `uio_in` directly over GPIO.

## How to Test

Verification workspace parameters rely on **cocotb** coupled with **Icarus Verilog (`iverilog`)**.

### Dependencies
Ensure your environment includes Python 3.11+ and the proper HDL toolchain packages:
```sh
pip install cocotb
sudo apt install iverilog
