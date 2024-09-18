import sys
import inspect

class MSNHandler():
    def __init__(self, func_table={}):
        self.func_table = dict(func_table)
    
    def handle(self, raw_data):
        if raw_data == '':
            sys.stderr.write("Received NULL")
            return
        components = raw_data.split()
        cmd = components.pop(0)
        if cmd in self.func_table:
            self.func_table[cmd](components)
        else:
            sys.stderr.write(f"Undefined function '{cmd}{components}'")
            try:
                self.func_table['error'](components)
            except KeyError:
                sys.stderr.write("No error function is defined. Consider adding one with a patcher entry for 'error'.")

    def patch_functions(self, patched):
        self.func_table.update(patched)
