#!/bin/bash

# Create all output directories.
for project in mlab-sandbox mlab-staging mlab-oti ; do
  mkdir -p gen/${project}/prometheus/{legacy-targets,blackbox-targets}
done

# All testing sites and machines.
SELECT_mlab_sandbox=$( cat plsync/testing_patterns.txt | xargs | sed -e 's/ /|/g' )

# All mlab4's and the set of canary machines.
SELECT_mlab_staging=$( cat plsync/staging_patterns.txt plsync/canary_machines.txt | xargs | sed -e 's/ /|/g' )

# All sites *excluding* test sites.
SELECT_mlab_oti=$( cat plsync/production_patterns.txt | xargs | sed -e 's/ /|/g' )


BASEDIR=${PWD}
for project in mlab-sandbox mlab-staging mlab-oti ; do
  pushd plsync
    output=${BASEDIR}/gen/${project}/prometheus

    # Construct the per-project SELECT variable name to use below.
    pattern=SELECT_${project/-/_}

    # Rsyncd on port 7999.
    ./mlabconfig.py --format=prom-targets \
        --template_target={{hostname}}:7999 \
        --label service=rsyncd \
        --label module=rsyncd_online \
        --rsync \
        --select "${!pattern}" > ${output}/blackbox-targets/rsyncd.json

    # SSH on port 806.
    ./mlabconfig.py --format=prom-targets-nodes \
        --template_target={{hostname}}:806 \
        --label service=ssh806 \
        --label module=ssh_v4_online \
        --select="${!pattern}" > ${output}/blackbox-targets/ssh806.json

    # Sidestream exporter in the npad experiment.
    ./mlabconfig.py --format=prom-targets \
        --template_target={{hostname}}:9090 \
        --label service=sidestream \
        --select "npad.iupui.(${!pattern})" > \
            ${output}/legacy-targets/sidestream.json
  popd
done
