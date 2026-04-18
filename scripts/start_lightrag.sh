#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"
export $(grep -v '^#' /opt/locus/lightrag.env | xargs)
echo yes | lightrag-server
