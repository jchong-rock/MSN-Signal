import auth.errors

class MSNPatcher():
    def __init__(self, connection):
        self.func_table = {}
        self.connection = connection
    def patch(self, handler):
        handler.patch_functions(self.func_table)
    # patching functions should have signature FUNC(self, data)

class ErrorPatcher(MSNPatcher):
    def __init__(self, connection):
        super().__init__(connection)
        self.func_table = {
            "error": self.__error__
        }
    
    def __error__(self, data):
        if len(data) >= 1:
            self.connection.error(auth.errors.GENERIC, data[0])