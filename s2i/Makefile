IMAGE_PREFIX = conda/s2i-conda-project
PLATFORM ?= local
TAG ?= latest
GIT_TAG = $(shell git describe --dirty --tags --long)
_comma = ,

ifeq ($(PLATFORM), local)
	DOCKER_BUILD=docker build
else
	DOCKER_BUILD=docker buildx build --platform $(PLATFORM) --push
endif

.base-image_%: Dockerfile $(wildcard s2i/bin/*) entrypoints/entrypoint.sh
	$(DOCKER_BUILD) -t $(IMAGE_PREFIX):$* .

dev: .base-image_dev

.PHONY: test-default-cmd-implicit
test-default-cmd-implicit: dev
	./tests/build-and-run.sh -d ./tests/default-cmd -i $(IMAGE_PREFIX):dev -c ""
.PHONY: test-default-cmd-explicit
test-default-cmd-explicit: dev
	./tests/build-and-run.sh -d ./tests/default-cmd -i $(IMAGE_PREFIX):dev -c default

test: test-default-cmd-implicit test-default-cmd-explicit
