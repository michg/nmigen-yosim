from vcd import VCDWriter

# Following code is from nMigen.
# Edited for compatibility
class VCDWaveformWriter:
    def __init__(self, simulation, signals, *, vcd_file):
        vcd_file = open(vcd_file, "wt")
        self.sim = simulation

        self.vcd_file = vcd_file
        self.vcd_writer = VCDWriter(self.vcd_file,
            timescale="1 ps", comment="Generated by nmigen-yosim")

        self.vcd_vars = []
        if self.vcd_writer is None:
            return

        for signal in signals:
            hierarchy = signal.name.split('.')
            var_type = "wire"
            var_size = signal.width
            var_init = signal.value
            var_name = hierarchy[-1]
            var_scope = '.'.join(hierarchy[:-1])

            vcd_var = self.vcd_writer.register_var(
                scope=var_scope, name=var_name,
                var_type=var_type, size=var_size, init=var_init)
            self.vcd_vars.append((vcd_var, signal))

    def update(self):
        timestamp = self.sim.sim_time
        for vcd_var, signal in self.vcd_vars:
            self.vcd_writer.change(vcd_var, timestamp, signal.value)

    def callback(self, signals):
        while True:
            self.update()
            yield

    def __del__(self):
        if self.vcd_writer is not None:
            self.vcd_writer.close(self.sim.sim_time)
        if self.vcd_file is not None:
            self.vcd_file.close()