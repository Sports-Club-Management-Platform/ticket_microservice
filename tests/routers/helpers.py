class DualAccessDict:
    def __init__(self, **kwargs):
        self._data = kwargs

    def __getitem__(self, key):
        return self._data[key]

    def __getattr__(self, key):
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError(f"'DualAccessDict' object has no attribute '{key}'")

    def __repr__(self):
        return repr(self._data)