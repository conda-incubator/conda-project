# Makefile for Sphinx documentation
#
# To get started, run `make live`

# Path to the documentation virtual environment
VENV = venv

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= $(VENV)/bin/sphinx-build
SPHINXAUTOBUILD ?= $(VENV)/bin/sphinx-autobuild
SPHINXAPIDOC  ?= $(VENV)/bin/sphinx-apidoc
SOURCEDIR     = source
BUILDDIR      = _build
APIDOCSDIR    = $(SOURCEDIR)/api

SRC = ../src/conda_project

# Internal variables.
ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees $(SPHINXOPTS) $(SOURCEDIR)

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Create a virtual environment
$(VENV):
	python -m venv $(VENV)

# Install docs dependencies
dev: $(VENV)
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -r requirements.txt

# Generate API docs via sphinx-apidoc
api-docs: dev
	$(SPHINXAPIDOC) -f -o $(APIDOCSDIR) $(SRC) -H "API Docs"

# Generate static HTML docs
html: api-docs
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

# Generate HTML docs and open in browser with live reload
live: api-docs
	$(SPHINXAUTOBUILD) "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O) --watch $(SRC) --open-browser

# Clean all build artifacts (doesn't remove virtual environment)
clean:
	rm -rf $(BUILDDIR) $(APIDOCSDIR)

.PHONY: help Makefile dev api-docs html live clean

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
