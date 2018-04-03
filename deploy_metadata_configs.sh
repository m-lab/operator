#!/bin/bash
#
# deploy_metadata_configs.sh does some things.

set -eux
set -o pipefail

# Root directory of this script.
SCRIPTDIR=$( dirname "${BASH_SOURCE[0]}" )
USAGE="$0 <keyname> <outdir> gs://<bucket-prefix>"
KEYNAME=${1:?Provide the service account keyname: $USAGE}
OUTDIR=${2:?Provide an output directory name: $USAGE}
BUCKET_TARGET=${3:?Provide an absolute GCS bucket and path for upload: $USAGE}

# Create all output directories.
mkdir -p ${OUTDIR}

# Copy user configs.
cp -r ${SCRIPTDIR}/metadata/v0/users ${OUTDIR}/

# TODO: Usage of .txt output is deprecated.
${SCRIPTDIR}/plsync/mlabconfig.py \
    --format=hostips > ${OUTDIR}/mlab-host-ips.txt

# Export standard JSON configs for host addresses and site status.
${SCRIPTDIR}/plsync/mlabconfig.py \
    --format=hostips-json > ${OUTDIR}/mlab-host-ips.json
${SCRIPTDIR}/plsync/mlabconfig.py \
    --format=sitestats > ${OUTDIR}/mlab-site-stats.json

# Use an archive date that equals the last commit date.
ARCHIVE=$( date -d @`cd ${SCRIPTDIR}; git log -1 --format=%ct` +%Y-%m-%dT%H:%M:00Z )

# TODO: Remove any files from 'current' that we are not generating.
# Get current list.
# Upload new files.
# Get new list.
# Delete old files.

# Upload "current" to GCS.
${SCRIPTDIR}/travis/deploy_gcs.sh \
  ${KEYNAME} ${OUTDIR}/* ${BUCKET_TARGET}/current/

# Copy "current" to archive.
${SCRIPTDIR}/travis/deploy_gcs.sh \
  ${KEYNAME} \
  ${BUCKET_TARGET}/current/* \
  ${BUCKET_TARGET}/archive/${ARCHIVE}/
