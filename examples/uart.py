from nmigen_yosim import *
from nmigen_yosim.vcd import VCDWaveformWriter
import random
import time
import subprocess
 


def reset_coroutine(rst, clk):
    rst.value = 1
    yield rising_edge(clk)
    rst.value = 0
    for i in range(3):
        yield rising_edge(clk)
    rst.value = 1
    yield rising_edge(clk)

def send_byte(net, val, period):
    net.value = 1
    yield timer(period, 'ns')
    net.value = 0
    yield timer(period, 'ns')
    for i in range(8):
        net.value =  val & 1
        val = val >> 1 
        yield timer(period, 'ns')
    net.value = 1
    yield timer(period, 'ns')

def uart_coroutine(net, baudrate, values):
    period = round(1/baudrate*1000*1000*1000)
    for val in values:
        yield from send_byte(net, val, period)
    
def main_coroutine(dut):
    yield from reset_coroutine(dut.resetn, dut.clk)
    dut.uart_rx_en.value = 1
    dut.uart_rxd.value = 1
    for i in range(10):
        yield rising_edge(dut.clk)
    yield from uart_coroutine(dut.uart_rxd, 12.5e6, b"Hello!")

def run_sim(name, vcd):
    for w in (32, 65, 120):
        sim_config = {
            'name' : name,
            'platform': None,
            'vcd_file': f'./dump_{w}.vcd' if vcd else None,
            'precision': (10, 'ns'),
            'debug' : False}

        with Simulator(**sim_config) as (sim, dut):
            start = time.time()
            clock_coro = clock(dut.clk, 20, 'ns')
            main_coro = main_coroutine(dut)
            sim.run([clock_coro, main_coro])
            elapsed = time.time() - start

        print(f'\nResults width={w} vcd={vcd}:')
        print(f'sim time: {sim.sim_time / 1000} ns')
        print(f'real time: {elapsed} s')
        print(f'simtime / realtime: {sim.sim_time / 1000 / elapsed} ns/s')

def genil(name):
    ilfile = name + '.il'
    vfile = name + '.v'
    subprocess.run(f'yosys -o {ilfile} {vfile}'.split(' '))
    return ilfile

if __name__ == '__main__':
    name = 'uart_rx'
    ilfile = genil(name)
    run_sim(name, vcd=True)
 
