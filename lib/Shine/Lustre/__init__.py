
class ServerError(Exception):
    """Any error related a specific Server."""
    def __init__(self, srv, message):
        Exception.__init__(self, message)
        self.server = srv

class ComponentError(Exception):
    """Generic exception for any components."""
    def __init__(self, comp, message):
        Exception.__init__(self, message)
        self.comp = comp
