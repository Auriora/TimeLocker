

class ResticError(Exception):
    pass

class ResticVersionError(ResticError):
    pass



class RepositoryError(ResticError):
    pass

class UnsupportedSchemeError(RepositoryError):
    pass