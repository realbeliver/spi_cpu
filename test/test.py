"""
test.py — cocotb testbench for tt_um_sem15_mul
SEM15 (1s/6e/8m, bias=31) floating-point multiplier
Result ready 1 clock after FIRE.

Protocol:
  uio_in[3:2] = CMD  (00=NOP, 01=LOAD_A, 10=LOAD_B, 11=FIRE)
  uio_in[4]   = BYTE_SEL  (0=low byte, 1=high byte)
  uio_in[6]   = RESULT_HI (0=result[7:0], 1=result[15:8])
  ui_in[7:0]  = data byte
  uio_out[0]  = out_valid (1 cycle pulse after FIRE)
  uo_out[7:0] = result byte
"""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ClockCycles

CMD_NOP    = 0b00
CMD_LOAD_A = 0b01
CMD_LOAD_B = 0b10
CMD_FIRE   = 0b11

def mk_uio(cmd=0, byte_sel=0, res_hi=0):
    return (cmd << 2) | (byte_sel << 4) | (res_hi << 6)

def to_q88(v):
    raw = int(round(v * 256))
    return max(-32768, min(32767, raw)) & 0xFFFF

def from_q88(raw):
    s = raw if raw < 32768 else raw - 65536
    return s / 256.0

async def reset(dut):
    dut.rst_n.value  = 0
    dut.ena.value    = 1
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value  = 1
    await ClockCycles(dut.clk, 3)

async def load_op(dut, cmd, val_q88):
    await FallingEdge(dut.clk)
    dut.ui_in.value  = val_q88 & 0xFF
    dut.uio_in.value = mk_uio(cmd=cmd, byte_sel=0)
    await FallingEdge(dut.clk)
    dut.ui_in.value  = (val_q88 >> 8) & 0xFF
    dut.uio_in.value = mk_uio(cmd=cmd, byte_sel=1)
    await FallingEdge(dut.clk)
    dut.ui_in.value  = 0
    dut.uio_in.value = mk_uio(cmd=CMD_NOP)

async def multiply(dut, a, b):
    """Load A and B, fire, read result. Returns float."""
    await load_op(dut, CMD_LOAD_A, to_q88(a))
    await load_op(dut, CMD_LOAD_B, to_q88(b))
    # FIRE
    await FallingEdge(dut.clk)
    dut.uio_in.value = mk_uio(cmd=CMD_FIRE)
    await RisingEdge(dut.clk)   # result registered on this edge
    await FallingEdge(dut.clk)
    dut.uio_in.value = mk_uio(cmd=CMD_NOP, res_hi=0)
    await RisingEdge(dut.clk); lo = dut.uo_out.value.to_unsigned()
    await FallingEdge(dut.clk)
    dut.uio_in.value = mk_uio(cmd=CMD_NOP, res_hi=1)
    await RisingEdge(dut.clk); hi = dut.uo_out.value.to_unsigned()
    dut.uio_in.value = 0
    return from_q88((hi << 8) | lo)

@cocotb.test()
async def test_basic(dut):
    """1.0 x 2.0 = 2.0"""
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    await reset(dut)
    r = await multiply(dut, 1.0, 2.0)
    dut._log.info(f"1.0 x 2.0 = {r:.4f}  expect 2.0")
    assert abs(r - 2.0) < 0.1

@cocotb.test()
async def test_fraction(dut):
    """1.5 x 2.0 = 3.0"""
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    await reset(dut)
    r = await multiply(dut, 1.5, 2.0)
    dut._log.info(f"1.5 x 2.0 = {r:.4f}  expect 3.0")
    assert abs(r - 3.0) < 0.1

@cocotb.test()
async def test_negative(dut):
    """-1.0 x 3.0 = -3.0"""
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    await reset(dut)
    r = await multiply(dut, -1.0, 3.0)
    dut._log.info(f"-1.0 x 3.0 = {r:.4f}  expect -3.0")
    assert abs(r - (-3.0)) < 0.1

@cocotb.test()
async def test_both_negative(dut):
    """-2.0 x -3.0 = 6.0"""
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    await reset(dut)
    r = await multiply(dut, -2.0, -3.0)
    dut._log.info(f"-2.0 x -3.0 = {r:.4f}  expect 6.0")
    assert abs(r - 6.0) < 0.1

@cocotb.test()
async def test_saturation(dut):
    """100 x 100 -> saturates to +127.996"""
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    await reset(dut)
    r = await multiply(dut, 100.0, 100.0)
    dut._log.info(f"100 x 100 = {r:.4f}  expect ~127.996 (sat)")
    assert r >= 127.9

@cocotb.test()
async def test_zero(dut):
    """0.0 x 5.0 = 0.0"""
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    await reset(dut)
    r = await multiply(dut, 0.0, 5.0)
    dut._log.info(f"0.0 x 5.0 = {r:.4f}  expect 0.0")
    assert abs(r) < 0.01

@cocotb.test()
async def test_small_fraction(dut):
    """0.25 x 0.25 = 0.0625"""
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    await reset(dut)
    r = await multiply(dut, 0.25, 0.25)
    dut._log.info(f"0.25 x 0.25 = {r:.4f}  expect 0.0625")
    assert abs(r - 0.0625) < 0.02

@cocotb.test()
async def test_large(dut):
    """7.5 x 3.0 = 22.5"""
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    await reset(dut)
    r = await multiply(dut, 7.5, 3.0)
    dut._log.info(f"7.5 x 3.0 = {r:.4f}  expect 22.5")
    assert abs(r - 22.5) < 0.5
