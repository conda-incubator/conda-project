# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import sys


def get_version():
    vi = sys.version_info

    return (vi.major, vi.minor, vi.micro)


if __name__ == "__main__":
    version = ".".join(str(i) for i in get_version())
    print(f"Python version {version}")
