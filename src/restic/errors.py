

class ResticError(Exception):
    pass

class ResticVersionError(ResticError):
    pass

class CommandExecutionError(ResticError):
    def __init__(self, message, stderr=None):
        super().__init__(message)
        self.stderr = stderr

class RepositoryError(ResticError):
    pass

class UnsupportedSchemeError(RepositoryError):
    pass