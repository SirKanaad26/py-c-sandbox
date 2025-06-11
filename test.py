from snappy_unsandboxed import snappy_wrapper
from snappy_sandbox.snappy.snappywasm import snappy_sandbox

snappy_sandboxed = snappy_sandbox.SnappyWasm()
compressed = snappy_sandboxed.compress(input_bytes)