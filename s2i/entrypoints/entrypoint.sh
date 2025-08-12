#!/bin/bash

if [ -e /opt/project/.assembled ]; then
    if [[ $1 == "/usr/libexec/s2i/run" ]]; then
        exec tini -g -- "$@"
    else
        exec tini -g -- conda-project run "$@"
    fi
else
    exec tini -g -- "$@"
fi
