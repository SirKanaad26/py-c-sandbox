from cython_snappy import CythonClass

if __name__ == "__main__":
    snappy = CythonClass()
    
    source_length = 1000  # Size in bytes of data you want to compress
    compressed_bound = snappy.cython_MaxCompressedLength(source_length)

    print(f"Maximum compressed size for {source_length} bytes: {compressed_bound}")
