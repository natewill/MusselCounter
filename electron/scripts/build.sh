#!/bin/bash
# Build script that increases file descriptor limit to handle large file trees

# Increase file descriptor limit
ulimit -n 4096

# Run electron-builder with all passed arguments
exec electron-builder "$@"

