from .dut import Dut
from .gen import generate_wrapper
from .vcd import VCDWaveformWriter
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

class Task:
    def __init__(self, coro, task_id):
        self.id = task_id
        self.coro = coro

class Simulator:
    def __init__(self, name, platform=None, ports=None, vcd_file=False, precision=(1, 'ps'), debug=False):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.il_file =  name + '.il'
        self.cpp_file = self.tmp_dir.name + '/' + name + '.cc'
        self.so_file = 'simulation.pyd'
        self.vcd_file = vcd_file
        self.name = name
        
        wrapper_path = os.path.dirname(os.path.realpath(__file__))
        self.wrapper_file = wrapper_path + '/wrapper.cc.j2'
        self.debug = debug

        self.cxxrtl()
        self.add_wrapper()
        self.build()

        spec = importlib.util.spec_from_file_location("simulation", self.so_file)
        self.sim = importlib.util.module_from_spec(spec)
        self.dut = Dut(self.sim)

        if self.vcd_file:
            self.vcd_writer = VCDWaveformWriter(simulation=self, vcd_file='./dump.vcd')
            self.vcd_signals = []

        self.set_precision(*precision)

    def cxxrtl(self):
        subprocess.run(f'yosys -o {self.cpp_file} {self.il_file}'.split(' ')
                      ).check_returncode()

    def add_wrapper(self):
        with open(self.wrapper_file) as f:
            wrapper = f.read()
        with open(self.cpp_file, 'r+') as f:
            cpp = f.read()
            wrapper = generate_wrapper(cpp=cpp, template=wrapper, name=self.name)
            f.write(wrapper)

    def build(self):
        python_incflags = subprocess.check_output(['sh','-c', 'python3-config --includes'], encoding="utf-8")
        python_ldflags = subprocess.check_output(['sh','-c', 'python3-config --ldflags'], encoding="utf-8")
        yosys_inc = os.path.join(os.path.split(os.path.split(shutil.which('yosys'))[0])[0], 'share','yosys','include')
        yosys_incflag = '-I'+yosys_inc
        print(yosys_incflag)
        debug_cflags = '-DDEBUG' if self.debug else ''
        vcd_cflags = '-DVCD_DUMP' if self.vcd_file else ''
        print
        subprocess.run(['clang++',
                        f'{self.cpp_file}',
                        yosys_incflag,
                        *python_incflags.split(' '),
                        '-shared', '-O3',
                        *python_ldflags.split(' '),
                        debug_cflags,
                        vcd_cflags,
                        '-o', f'{self.so_file}'])

    def run(self, coros):
        tasks = []
        if self.vcd_file:
            if not self.vcd_signals:
                self.vcd_signals = self.dut.get_signals(recursive=True)
            self.vcd_callback = self.vcd_writer.callback(self.vcd_signals)
            self.sim.set_vcd_callback(self.vcd_callback)

        for coro in coros:
            tasks.append(Task(coro, 0))
            self.sim.add_task(coro)
        try:
            try:
                self.sim.scheduller()
            except Exception as e:
                raise e.__cause__ from None
        except StopIteration:
            pass

    @property
    def sim_time(self):
        return self.sim.get_sim_time()

    def set_precision(self, value, units='ps'):
        mult = 1 if units == 'ps' else \
               10**3 if units == 'ns' else \
               10**6 if units == 'us' else \
               10**9 if units == 's' else \
               None
        if not mult:
            raise ValueError('Invalid unit')
        return self.sim.set_sim_time_precision(value * mult)

    def fork(self, coro):
        task_id = self.sim.fork(coro)
        return Task(coro, task_id)

    def __enter__(self):
        return self, self.dut

    def __exit__(self, exception_type, exception_val, trace):
        pass
