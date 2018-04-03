#!/bin/bash
#
# deploy_metadata_configs.sh generates and archives standard M-Lab site, host,
# and experiment configuration information.
#
# To prevent duplicates, archives are only updated when sites.py or slices.py
# change. It is safe to run deploy_metadata_configs.sh multiple times.
#
# Example:
#  ./deploy_metadata_configs.sh
#      SERVICE_ACCOUNT_mlab_sandbox
#      $TRAVIS_BUILD_DIR/gen/mlab-sandbox
#      gs://operator-mlab-sandbox/metadata/v0

set -eux
set -o pipefail

# Root directory of this script.
SCRIPTDIR=$( dirname "${BASH_SOURCE[0]}" )
USAGE="$0 <keyname> <output-dir> <gs://bucket/and/path>"
KEYNAME=${1:?Provide the service account keyname: $USAGE}
OUTDIR=${2:?Provide an output directory name: $USAGE}
BUCKET_TARGET=${3:?Provide an absolute GCS bucket and path for upload: $USAGE}

############################################################################
# Generate configs
############################################################################
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

############################################################################
# Upload and archive configs
############################################################################

# Archive date is the most recent commit time to slices.py or sites.py.
TIMESTAMP=$( cd ${SCRIPTDIR}; \
    for f in plsync/sites.py plsync/slices.py ; do \
      git log -1 --format=%ct $f ; \
    done | sort -nr | head -1)
ARCHIVE=$( date -d @${TIMESTAMP} +%Y-%m-%dT%H:%M:%SZ )

# Check whether the current ARCHIVE date already exists. If so, then a previous
# deploy already uploaded it. If not, then we'll upload it below.
if gsutil stat ${BUCKET_TARGET}/archive/${ARCHIVE}/mlab-site-stats.json ; then
  echo "Skipping upload because the current archive is already up to date!"
  exit 0
fi

# TODO: Remove any files from 'current' that we are not generating.

# Upload generated files to "current" directory in GCS.
${SCRIPTDIR}/travis/deploy_gcs.sh \
  ${KEYNAME} \
  ${OUTDIR}/* \
  ${BUCKET_TARGET}/current/

# Create an archive copy of the new "current" directory.
${SCRIPTDIR}/travis/deploy_gcs.sh \
  ${KEYNAME} \
  ${BUCKET_TARGET}/current/* \
  ${BUCKET_TARGET}/archive/${ARCHIVE}/
