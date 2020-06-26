import jinja2
import re
import sys


class ModuleParserFsm:
    START = 0
    ELEMENTS = 1
    RE_START_MODULE = re.compile(r'struct (\S*) : public module {')
    RE_END_MODULE = re.compile('}; // struct \S*')
    RE_WIRE = re.compile(r'wire<(\d*)> (\S*).*;')
    RE_INPUT = re.compile(r'/\*input\*/ value<(\d*)> (\S*).*;')
    RE_CELL = re.compile(r'(\S*) cell_(\S*);')
    def __init__(self):
        self.state = self.START
        self.modules = {}
        self.current = None
    def add_module(self, name):
        self.modules[name] = {'wires': [], 'cells': [], 'inputs': []}
    def add_wire(self, name, width):
        self.modules[self.current]['wires'].append((name, width))
    def add_input(self, name, width):
        self.modules[self.current]['inputs'].append((name, width))
    def add_cell(self, name):
        self.modules[self.current]['cells'].append(name)
    def parse(self, c_file):
        for l in c_file.split('\n'):
            if self.state == self.START:
                found = self.RE_START_MODULE.findall(l)
                if found:
                    module = found[0]
                    self.add_module(module)
                    self.current = module
                    self.state = self.ELEMENTS
            elif self.state == self.ELEMENTS:
                found = self.RE_WIRE.findall(l)
                if found:
                    self.add_wire(name=found[0][1], width=found[0][0])
                else:
                    found = self.RE_INPUT.findall(l)
                    if found:
                        #breakpoint()
                        self.add_input(name=found[0][1], width=found[0][0])
                    else:
                        found = self.RE_CELL.findall(l)
                        if found:
                            self.add_cell(name=found[0][1])
                        else:
                            if self.RE_END_MODULE.findall(l):
                                self.state = self.START
        return self.modules

class Wire:
    def __init__(self, name, width, hierarchy, io=False):
        self.name = name
        self.width = width
        self.hierarchy = hierarchy
        self.io = io

    def nmigen_path(self):
        hierarchy = [h[2:] for h in self.hierarchy]
        name = self.name[2:]
        if self.io:
            name = name.replace('__','_')
        return '.'.join(hierarchy) + '.' + name

    def c_path(self):
        path = '.cell_'.join(self.hierarchy) + f'.{self.name}'
        path = path[2:]
        return path

    def __str__(self):
        return nmigen_path

    def __dict__(self):
        return {'name': self.nmigen_path(), 'cpath': self.c_path(), 'width':self.width}

class WiresExtractor:
    def __init__(self, modules):
        self.modules = modules

    def extract(self, cell, hierarchy=None):
        wires = []
        inputs = []
        if not hierarchy:
            hierarchy = []
        else:
            hierarchy = list(hierarchy)
        hierarchy.append(cell)
        for wire, width in self.modules[cell]['wires']:
            wires.append(Wire(wire, width, hierarchy))
        for wire, width in self.modules[cell]['inputs']:
            inputs.append(Wire(wire, width, hierarchy, io=True))

        for c in self.modules[cell]['cells']:
            c_wires = self.extract(c, hierarchy)
            if c_wires:
                wires.extend(c_wires)
        return wires, inputs

def generate_wrapper(cpp, template, name):
    modules = ModuleParserFsm().parse(cpp)
    namec = name.replace('_','__')
    wires, inputs = WiresExtractor(modules).extract(f'p_{namec}')
    wires_dict = [w.__dict__() for w in wires]
    inputs_dict = [w.__dict__() for w in inputs]
    t = jinja2.Template(template)
    wrapper = t.render(wires=wires_dict, inputs=inputs_dict, name=namec)
    return wrapper
