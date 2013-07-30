
class ComponentError(Exception):
    """Generic exception for any components."""
    def __init__(self, comp, message):
        Exception.__init__(self, message)
        self.comp = comp
