# -*- coding: utf-8 -*-
# Copyright (C) 2022 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from ..project import load_project


def prepare(args):
    project = load_project(args.directory)
    project.prepare(args.force)
    return 0


def clean(args):
    project = load_project(args.directory)
    project.clean()
    return 0
