class Tainted:
    def __init__(self, value):
        self._value = value

    def copy_and_verify(self, verifier):
        v = verifier(self._value)
        if v is None:
            raise ValueError("Verification failed")
        return v

    def UNSAFE_unverified(self):
        return self._value
