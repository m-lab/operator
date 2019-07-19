#!/bin/bash

set -euxo pipefail

# Root directory of this script.
SCRIPTDIR=$( dirname "${BASH_SOURCE[0]}" )
BASEDIR=${PWD}

# Create all output directories.
for project in mlab-sandbox mlab-staging mlab-oti ; do
  mkdir -p ${BASEDIR}/gen/${project}/prometheus/{legacy-targets,blackbox-targets,blackbox-targets-ipv6,snmp-targets,script-targets}
done

# All testing sites and machines.
SELECT_mlab_sandbox=$( cat ${SCRIPTDIR}/plsync/testing_patterns.txt | xargs | sed -e 's/ /|/g' )

# All mlab4's and the set of canary machines.
SELECT_mlab_staging=$( cat ${SCRIPTDIR}/plsync/staging_patterns.txt | xargs | sed -e 's/ /|/g' )

# All sites *excluding* test sites.
SELECT_mlab_oti=$( cat ${SCRIPTDIR}/plsync/production_patterns.txt | xargs | sed -e 's/ /|/g' )

# GCP doesn't support IPv6, so we have a Linode VM running three instances of
# the blackbox_exporter, on three separate ports... one port/instance for each
# project. These variables map projects to ports, and will be transmitted to
# Prometheus in the form of a new label that will be rewritten.
BBE_IPV6_PORT_mlab_oti="9115"
BBE_IPV6_PORT_mlab_staging="8115"
BBE_IPV6_PORT_mlab_sandbox="7115"


for project in mlab-sandbox mlab-staging mlab-oti ; do
  pushd ${SCRIPTDIR}/plsync
    output=${BASEDIR}/gen/${project}/prometheus

    # Construct the per-project SELECT variable name to use below.
    pattern=SELECT_${project/-/_}

    # Construct the per-project blackbox_exporter port variable to use below.
    # blackbox_exporter on for IPv6 targets.
    bbe_port=BBE_IPV6_PORT_${project/-/_}

    # Rsyncd on port 7999.
    ./legacyconfig.py --format=prom-targets \
        --template_target={{hostname}}:7999 \
        --label service=rsyncd \
        --label module=rsyncd_online \
        --rsync \
        --select "${!pattern}" > ${output}/blackbox-targets/rsyncd.json

    # SSH on port 806 over IPv4
    ./legacyconfig.py --format=prom-targets-nodes \
        --template_target={{hostname}}:806 \
        --label service=ssh806 \
        --label module=ssh_v4_online \
        --select "${!pattern}" > ${output}/blackbox-targets/ssh806.json

    # SSH on port 806 over IPv6
    ./legacyconfig.py --format=prom-targets-nodes \
        --template_target={{hostname}}:806 \
        --label service=ssh806 \
        --label module=ssh_v6_online \
        --label __blackbox_port=${!bbe_port} \
        --select "${!pattern}" \
        --decoration "v6" > ${output}/blackbox-targets-ipv6/ssh806_ipv6.json

    # Sidestream exporter in the npad experiment.
    ./legacyconfig.py --format=prom-targets \
        --template_target={{hostname}}:9090 \
        --label service=sidestream \
        --select "npad.iupui.(${!pattern})" > \
            ${output}/legacy-targets/sidestream.json
  popd
done
