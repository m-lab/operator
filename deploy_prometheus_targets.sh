#!/bin/bash

set -e
set -x
set -u

USAGE="Usage: $0 <project>"
PROJECT=${1:?Please provide project name: $USAGE}

# Root directory of this script.
SCRIPTDIR=$( dirname "${BASH_SOURCE[0]}" )
BASEDIR=${PWD}

# Generate the configs.
${SCRIPTDIR}/generate_prometheus_targets.sh

# Copy the configs to GCS.
${SCRIPTDIR}/travis/deploy_gcs_copy.sh \
  /tmp/${PROJECT}.json \
  ${BASEDIR}/gen/${PROJECT}/prometheus \
  gs://operator-${PROJECT} -r
