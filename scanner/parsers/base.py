class Parser:
    """Base class for language-specific parsers."""
    def parse(self, content):
        raise NotImplementedError("Subclasses must implement parse()")
