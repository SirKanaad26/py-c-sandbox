# validators.py

from ctypes import Union
from typing import List


def validate_max_compressed_length(source_length: int, result: int):
    """Validate the result returned by MaxCompressedLength."""
    print("validating")
    if not isinstance(result, int):
        raise ValueError("Result from MaxCompressedLength must be an integer.")

    if result < source_length:
        raise ValueError(f"Invalid compressed length: {result} < source_length ({source_length})")

    if result > source_length * 2 + 64:
        raise ValueError(f"Compressed length too large: {result} for input size {source_length}")

def validate_uncompressed_length(compressed_len: int, result: int):
    """Validate the output of GetUncompressedLength."""
    print("validating Uncompressed length")
    if not isinstance(result, int):
        raise ValueError("Uncompressed length must be an integer.")

    if result <= 0:
        raise ValueError("Uncompressed length must be greater than 0.")

    if result > compressed_len * 100:
        raise ValueError(f"Uncompressed length too large: {result} for compressed size {compressed_len}")

def validate_compressed_output(input_len: int, max_out_len: int, compressed_len: int):
    """Validate the result length of a compression operation."""
    if not isinstance(compressed_len, int):
        raise ValueError("Compressed length must be an integer.")

    if compressed_len <= 0:
        raise ValueError("Compressed length must be positive.")

    if compressed_len > max_out_len:
        raise ValueError(f"Compressed length {compressed_len} exceeds max allowed {max_out_len}")

    if compressed_len >= input_len:
        # Compression usually reduces size, warn if it doesn't
        print(f"[WARNING] Compressed length ({compressed_len}) >= input length ({input_len}) — possible inefficiency.")

def validate_iovec_compressed_output(total_input_len: int, max_out_len: int, compressed_len: int):
    """Validate compressed output length from CompressFromIOVec."""
    if not isinstance(compressed_len, int):
        raise ValueError("Compressed length must be an integer.")

    if compressed_len <= 0:
        raise ValueError("Compressed length must be greater than 0.")

    if compressed_len > max_out_len:
        raise ValueError(f"Compressed length {compressed_len} exceeds max allowed {max_out_len}")

    if compressed_len >= total_input_len:
        print(f"[WARNING] Compressed length ({compressed_len}) >= input length ({total_input_len}).")

def validate_uncompress_output(compressed_len: int, expected_uncompressed_len: int, actual_uncompressed_len: int):
    """Validate the length of the uncompressed output returned from WASM."""
    if not isinstance(actual_uncompressed_len, int):
        raise ValueError("Uncompressed length must be an integer.")

    if actual_uncompressed_len <= 0:
        raise ValueError("Uncompressed length must be greater than zero.")

    if actual_uncompressed_len > expected_uncompressed_len * 2:
        raise ValueError(
            f"Uncompressed length {actual_uncompressed_len} is unreasonably large compared to expected {expected_uncompressed_len}."
        )

    if actual_uncompressed_len < expected_uncompressed_len // 4:
        print(
            f"[WARNING] Uncompressed length ({actual_uncompressed_len}) much smaller than expected ({expected_uncompressed_len})"
        )

def validate_raw_uncompressed_output(expected_len: int, output: bytes):
    """Validate the result of raw uncompression."""
    if not isinstance(output, bytes):
        raise ValueError("Output must be of type 'bytes'.")

    actual_len = len(output)

    if actual_len == 0:
        raise ValueError("Uncompressed output is empty.")

    if actual_len != expected_len:
        raise ValueError(
            f"Uncompressed length mismatch: got {actual_len}, expected {expected_len}"
        )

def validate_raw_uncompress_to_iovec_output(expected_total_len: int, output_buffers: List[bytes]):
    """Validate output of RawUncompressToIOVec."""
    if not isinstance(output_buffers, list):
        raise ValueError("Output must be a list of byte buffers.")

    total_len = sum(len(buf) for buf in output_buffers)

    if total_len == 0:
        raise ValueError("All output buffers are empty.")

    if total_len != expected_total_len:
        raise ValueError(
            f"Total uncompressed length mismatch: expected {expected_total_len}, got {total_len}"
        )

    for i, buf in enumerate(output_buffers):
        if not isinstance(buf, bytes):
            raise ValueError(f"Buffer {i} is not of type 'bytes'.")

def validate_raw_uncompress_to_iovec_output(expected_total_len: int, output_buffers: List[bytes]):
    """Validate output of RawUncompressToIOVec-style functions."""
    if not isinstance(output_buffers, list):
        raise ValueError("Output must be a list of byte buffers.")

    total_len = sum(len(buf) for buf in output_buffers)

    if total_len == 0:
        raise ValueError("All output buffers are empty.")

    if total_len != expected_total_len:
        raise ValueError(
            f"Total uncompressed length mismatch: expected {expected_total_len}, got {total_len}"
        )

    for i, buf in enumerate(output_buffers):
        if not isinstance(buf, bytes):
            raise ValueError(f"Buffer {i} is not of type 'bytes'.")

def validate_raw_uncompress_to_iovec_output(expected_total_len: int, output_buffers: List[bytes]):
    """Validate output of RawUncompressToIOVec-style functions."""
    if not isinstance(output_buffers, list):
        raise ValueError("Output must be a list of byte buffers.")

    total_len = sum(len(buf) for buf in output_buffers)

    if total_len == 0:
        raise ValueError("All output buffers are empty.")

    if total_len != expected_total_len:
        raise ValueError(
            f"Total uncompressed length mismatch: expected {expected_total_len}, got {total_len}"
        )

    for i, buf in enumerate(output_buffers):
        if not isinstance(buf, bytes):
            raise ValueError(f"Buffer {i} is not of type 'bytes'.")

def validate_raw_uncompress_to_buffers_output(expected_total_len: int, buffer_sizes: List[int], output_buffers: List[bytes]):
    """
    Validate the output of RawUncompressToBuffers.
    
    Checks:
    - Output is a list of bytes objects
    - Each buffer matches the corresponding expected size
    - Total length matches expected uncompressed length
    """
    if not isinstance(output_buffers, list):
        raise ValueError("Output must be a list.")

    if len(buffer_sizes) != len(output_buffers):
        raise ValueError(
            f"Mismatch between number of expected buffers ({len(buffer_sizes)}) and actual ({len(output_buffers)})."
        )

    for i, (expected_size, buf) in enumerate(zip(buffer_sizes, output_buffers)):
        if not isinstance(buf, bytes):
            raise ValueError(f"Buffer {i} is not of type 'bytes'.")
        if len(buf) != expected_size:
            raise ValueError(
                f"Buffer {i} size mismatch: expected {expected_size}, got {len(buf)}"
            )

    actual_total = sum(len(buf) for buf in output_buffers)
    if actual_total != expected_total_len:
        raise ValueError(
            f"Total output size mismatch: expected {expected_total_len}, got {actual_total}"
        )

def validate_is_valid_compressed_buffer_result(compressed_data: bytes, result: bool):
    """Validate output of is_valid_compressed_buffer()."""
    if not isinstance(result, bool):
        raise ValueError("Result must be of type bool.")

    if not isinstance(compressed_data, (bytes, bytearray)):
        raise ValueError("Compressed data must be of type bytes or bytearray.")

    if len(compressed_data) == 0 and result:
        raise ValueError("Empty buffer cannot be validly compressed.")


def validate_is_valid_compressed_result(compressed_data: bytes, result: bool):
    """Validate output of is_valid_compressed()."""
    if not isinstance(result, bool):
        raise ValueError("Result must be of type bool.")

    if not isinstance(compressed_data, (bytes, bytearray)):
        raise ValueError("Compressed data must be of type bytes or bytearray.")

    if len(compressed_data) == 0 and result:
        raise ValueError("Empty buffer cannot be validly compressed.")

def validate_compression_level_result(level: int, label: str):
    if not isinstance(level, int):
        raise ValueError(f"{label} must be an integer.")
    if level < 0 or level > 100:
        raise ValueError(f"{label} is out of expected range: {level}")

def validate_compression_info(info: dict):
    min_level = info["min_level"]
    max_level = info["max_level"]
    default_level = info["default_level"]

    if not (min_level <= default_level <= max_level):
        raise ValueError(f"Default level {default_level} is not between min {min_level} and max {max_level}")

def validate_raw_uncompress_buffer_output(compressed_data: bytes, uncompressed_buffer: bytearray, success: bool):
    """Validate the output of raw_uncompress with provided bytearray."""
    if not isinstance(success, bool):
        raise ValueError("Return value must be of type bool.")

    if not isinstance(uncompressed_buffer, bytearray):
        raise ValueError("uncompressed_buffer must be a bytearray.")

    if not isinstance(compressed_data, (bytes, bytearray)):
        raise ValueError("compressed_data must be bytes or bytearray.")

    if success:
        if len(uncompressed_buffer) == 0:
            raise ValueError("Uncompressed buffer should not be empty if decompression succeeded.")
        if all(b == 0 for b in uncompressed_buffer):
            raise ValueError("Uncompressed buffer appears to be empty (all zeros) despite success.")

def validate_raw_uncompress_to_iovec_from_source_output(
    compressed_data: bytes,
    buffer_sizes: List[int],
    output_buffers: List[bytes],
    expected_total_len: int = None
):
    """Validate output from raw_uncompress_to_iovec_from_source."""
    if not isinstance(output_buffers, list):
        raise ValueError("Output must be a list of byte buffers.")

    if len(output_buffers) != len(buffer_sizes):
        raise ValueError(
            f"Number of output buffers ({len(output_buffers)}) does not match buffer_sizes ({len(buffer_sizes)})."
        )

    for i, (buf, expected_size) in enumerate(zip(output_buffers, buffer_sizes)):
        if not isinstance(buf, bytes):
            raise ValueError(f"Output buffer {i} is not of type 'bytes'.")
        if len(buf) != expected_size:
            raise ValueError(f"Output buffer {i} size mismatch: expected {expected_size}, got {len(buf)}")

    total_output_len = sum(len(b) for b in output_buffers)

    if expected_total_len is not None and total_output_len != expected_total_len:
        raise ValueError(
            f"Total output size mismatch: expected {expected_total_len}, got {total_output_len}"
        )

    if total_output_len == 0:
        raise ValueError("All output buffers are empty.")

def validate_raw_compress_output(input_data: bytes, output_data: bytes, max_expected_len: int):
    """Validate output of raw_compress()."""
    if not isinstance(output_data, bytes):
        raise ValueError("Compressed output must be of type bytes.")

    input_len = len(input_data)
    output_len = len(output_data)

    if input_len == 0 and output_len != 0:
        raise ValueError("Expected empty output for empty input, got non-empty output.")

    if input_len != 0 and output_len == 0:
        raise ValueError("Compression failed: got empty output for non-empty input.")

    if output_len > max_expected_len:
        raise ValueError(f"Compressed output ({output_len}) exceeds estimated max ({max_expected_len}).")

    # Optional: warn if compression was ineffective
    if output_len >= input_len:
        print(f"[WARNING] Compressed output ({output_len}) >= input ({input_len}). Inefficient compression.")

def validate_raw_compress_with_options_output(
    input_data: bytes,
    output_data: bytes,
    max_expected_len: int,
    compression_level: int,
    min_level: int = 1,
    max_level: int = 10,
):
    """Validate output of raw_compress_with_options()."""
    if not isinstance(output_data, bytes):
        raise ValueError("Compressed output must be of type bytes.")

    if not isinstance(compression_level, int):
        raise ValueError("Compression level must be an integer.")

    if not (min_level <= compression_level <= max_level):
        raise ValueError(f"Compression level {compression_level} is out of supported range [{min_level}, {max_level}].")

    input_len = len(input_data)
    output_len = len(output_data)

    if input_len == 0 and output_len != 0:
        raise ValueError("Expected empty output for empty input, got non-empty output.")

    if input_len != 0 and output_len == 0:
        raise ValueError("Compression failed: got empty output for non-empty input.")

    if output_len > max_expected_len:
        raise ValueError(f"Compressed output ({output_len}) exceeds estimated max ({max_expected_len}).")

    if output_len >= input_len:
        print(f"[WARNING] Compressed output ({output_len}) >= input ({input_len}) — inefficient compression.")


def validate_raw_compress_from_iovec_output(data_buffers: List[Union[bytes, bytearray]], output_data: bytes, max_expected_len: int):
    """Validate output of raw_compress_from_iovec()."""
    if not isinstance(output_data, bytes):
        raise ValueError("Compressed output must be of type bytes.")

    total_input_len = sum(len(buf) for buf in data_buffers)
    output_len = len(output_data)

    if total_input_len == 0 and output_len != 0:
        raise ValueError("Expected empty output for empty input, got non-empty output.")

    if total_input_len != 0 and output_len == 0:
        raise ValueError("Compression failed: got empty output for non-empty input.")

    if output_len > max_expected_len:
        raise ValueError(f"Compressed output length {output_len} exceeds expected max {max_expected_len}.")

    if output_len >= total_input_len:
        print(f"[WARNING] Compressed size {output_len} ≥ input size {total_input_len} — compression might be inefficient.")


def validate_raw_compress_from_iovec_with_options_output(
    data_buffers: List[Union[bytes, bytearray]],
    output_data: bytes,
    max_expected_len: int,
    options: int,
    min_level: int,
    max_level: int
):
    """Validate output of raw_compress_from_iovec_with_options()."""
    if not isinstance(output_data, bytes):
        raise ValueError("Compressed output must be of type bytes.")

    if not isinstance(options, int):
        raise ValueError("Compression option must be an integer.")

    if options < min_level or options > max_level:
        raise ValueError(f"Compression option {options} is out of valid range [{min_level}, {max_level}].")

    total_input_len = sum(len(b) for b in data_buffers)
    output_len = len(output_data)

    if total_input_len == 0 and output_len != 0:
        raise ValueError("Expected empty output for empty input, got non-empty output.")

    if total_input_len != 0 and output_len == 0:
        raise ValueError("Compression failed: got empty output for non-empty input.")

    if output_len > max_expected_len:
        raise ValueError(f"Compressed output length {output_len} exceeds max allowed {max_expected_len}.")

    if output_len >= total_input_len:
        print(f"[WARNING] Compressed output ({output_len}) >= input ({total_input_len}) — inefficient compression.")

