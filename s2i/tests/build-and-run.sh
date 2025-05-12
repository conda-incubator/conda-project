#!/bin/bash
#
# The 'run' performs a simple test that verifies the S2I image.
# The main focus here is to exercise the S2I scripts.
#
# For more information see the documentation:
# https://github.com/openshift/source-to-image/blob/master/docs/builder_image.md
#

PROJECT=
BUILDER_IMAGE="conda/s2i-conda-project:dev"
COMMAND="default"

while getopts "d:i:c:r:" flag; do
  case $flag in
    d) PROJECT=${OPTARG} ;;
    i) BUILDER_IMAGE=${OPTARG} ;;
    c) COMMAND=${OPTARG} ;;
  esac
done

shift $((OPTIND - 1))

if [[ -z $PROJECT ]]; then
  echo "The argument -d <project-directory> is required" >&2
  exit 1
fi

TAG="test-$(basename $PROJECT)"

# Determining system utility executables (darwin compatibility check)
READLINK_EXEC="readlink -zf"
MKTEMP_EXEC="mktemp --suffix=.cid"
if [[ "$OSTYPE" =~ 'darwin' ]]; then
  READLINK_EXEC="readlink"
  MKTEMP_EXEC="mktemp"
  ! type -a "greadlink" &>"/dev/null" || READLINK_EXEC="greadlink"
  ! type -a "gmktemp" &>"/dev/null" || MKTEMP_EXEC="gmktemp"
fi

_dir="$(dirname "${BASH_SOURCE[0]}")"
test_dir="$($READLINK_EXEC ${_dir} || echo ${_dir})"
image_dir=$($READLINK_EXEC ${test_dir}/.. || echo ${test_dir}/..)
scripts_url="${image_dir}/.s2i/bin"
cid_file=$($MKTEMP_EXEC -u)

# Since we built the candidate image locally, we don't want S2I to attempt to pull
# it from Docker hub
s2i_args="--pull-policy=never --loglevel=2"

#Port the image exposes service to be tested
test_port=8086

image_exists() {
  docker inspect $1 &>/dev/null
}

container_exists() {
  image_exists $(cat $cid_file)
}

container_ip() {
  docker inspect --format="{{(index .NetworkSettings.Ports \"$test_port/tcp\" 0).HostIp }}" $(cat $cid_file) | sed 's/0.0.0.0/localhost/'
}

container_port() {
  docker inspect --format="{{(index .NetworkSettings.Ports \"$test_port/tcp\" 0).HostPort }}" "$(cat "${cid_file}")"
}

run_s2i_build() {
  if ! image_exists ${BUILDER_IMAGE}; then
    echo "ERROR: The image ${BUILDER_IMAGE} must exist before this script is executed."
    exit 1
  fi
  s2i build -c ${s2i_args} ${PROJECT} ${BUILDER_IMAGE} ${TAG} -e CMD=${COMMAND}
}

run_command() {
  docker run --rm --cidfile=${cid_file} -p ${test_port}:${test_port} ${TAG} ${COMMAND} | grep -Fx "${COMMAND:-default}"
}

cleanup() {
  if [ -f $cid_file ]; then
    if container_exists; then
      docker stop $(cat $cid_file)
    fi
  fi
  if image_exists ${TAG}; then
    docker rmi ${TAG}
  fi
}

check_result() {
  local result="$1"
  if [[ "$result" != "0" ]]; then
    echo "S2I image '${BUILDER_IMAGE}' test FAILED (exit code: ${result})"
    cleanup
    exit $result
  fi
}

wait_for_cid() {
  local max_attempts=10
  local sleep_time=1
  local attempt=1
  local result=1
  while [ $attempt -le $max_attempts ]; do
    [ -f $cid_file ] && break
    echo "Waiting for container to start..."
    attempt=$(( $attempt + 1 ))
    sleep $sleep_time
  done
}

test_usage() {
  echo "Testing 's2i usage'..."
  s2i usage ${s2i_args} ${BUILDER_IMAGE} &>/dev/null
}

# Build the project image
run_s2i_build
ret=$?
check_result $ret

# Verify the 'usage' script is working properly
test_usage
check_result $?

echo "Testing command ${COMMAND}"
run_command
ret=$?

# Wait for the container to write its CID file
wait_for_cid

check_result $ret

cleanup
