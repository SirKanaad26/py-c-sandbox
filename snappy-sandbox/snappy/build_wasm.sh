em++ \
  -I. -Isrc \
  src/snappy.cc src/snappy-sinksource.cc src/snappy-stubs-internal.cc \
  snappy_wrapper.cc \
  -o snappy.js \
  -s MODULARIZE \
  -s EXPORT_NAME=createSnappyModule \
  -s WASM=1 \
  --bind
