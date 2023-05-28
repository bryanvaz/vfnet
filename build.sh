#!/bin/bash

# Check if the script was called with the "release" parameter
if [[ "$1" == "release" ]]; then
    # Create a GitHub release without building
    version=$(./vfnet --version)
    gh release create "v$version" --title "v$version" --notes "Release notes for v$version" \
      --draft \
      ./dist/vfnet \
      ./dist/vfnet.bin \
      ./dist/vfnet.dev.bin
else
    # Build the Docker image
    docker build -t vfnet_build_container -f Dockerfile .

    # Run the build container with a bind mount to the current project folder
    # docker run -v $(pwd):/app -w /app/src --entrypoint pyinstaller vfnet_build_container --onefile --clean --add-data "vfup:." --name vfnet main.py

    rm -rf dist build

    docker run -v $(pwd):/app -w /app/src --entrypoint pyinstaller vfnet_build_container --workpath /app/build --distpath /app/dist --onefile --clean --add-data "vfup:." --name vfnet.dev.bin __main__.py


    docker run -v $(pwd):/app -w /app/src --entrypoint pyinstaller vfnet_build_container --strip --workpath /app/build --distpath /app/dist --onefile --add-data "vfup:." --name vfnet.bin __main__.py

    mkdir -p build/vfnet.bundle dist

    cp -R src/* build/vfnet.bundle/

    rm -rf build/vfnet.bundle/__pycache__ \
      build/vfnet.bundle/*.spec \
      build/vfnet.bundle/*.pyc \
      build/vfnet.bundle/*.pyo \
      build/vfnet.bundle/*.pyd \
      build/vfnet.bundle/*.log \
      build/vfnet.bundle/*.zip \
      build/vfnet.bundle/*.dist \
      build/vfnet.bundle/*.dist-info \
      build/vfnet.bundle/*.egg-info \
      build/vfnet.bundle/*.exe

    cd build/vfnet.bundle/ && zip -r ../vfnet.bundle.zip *
    cd ..
    echo '#!/usr/bin/env python3' | cat - vfnet.bundle.zip > ../dist/vfnet
    chmod +x ../dist/vfnet
fi
