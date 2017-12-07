#!/bin/bash


# Root directory of this script.
SCRIPTDIR=$( dirname "${BASH_SOURCE[0]}" )
BASEDIR=${PWD}

USAGE="Usage: $0 <GROUP>"
GROUP=${1:?Please provide monitoring group name: $USAGE}

# Create all output directories.
for project in mlab-sandbox mlab-staging mlab-oti ; do
  mkdir -p ${BASEDIR}/gen/${project}/prometheus/{legacy-targets,blackbox-targets,snmp-targets}
done

# All testing sites and machines.
SELECT_mlab_sandbox=$( cat ${SCRIPTDIR}/plsync/testing_patterns.txt | xargs | sed -e 's/ /|/g' )

# All mlab4's and the set of canary machines.
SELECT_mlab_staging=$( cat ${SCRIPTDIR}/plsync/staging_patterns.txt ${SCRIPTDIR}/plsync/canary_machines.txt | xargs | sed -e 's/ /|/g' )

# All sites *excluding* test sites.
SELECT_mlab_oti=$( cat ${SCRIPTDIR}/plsync/production_patterns.txt | xargs | sed -e 's/ /|/g' )


for project in mlab-sandbox mlab-staging mlab-oti ; do
  pushd ${SCRIPTDIR}/plsync
    output=${BASEDIR}/gen/${project}/prometheus

    # Construct the per-project SELECT variable name to use below.
    pattern=SELECT_${project/-/_}

    if [[ ${GROUP} == scraper ]] ; then
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

    elif [[ ${GROUP} == global ]] ; then

      # NDT "raw" on port 3001.
      ./mlabconfig.py --format=prom-targets \
          --template_target={{hostname}}:3001 \
          --label service=ndt_raw \
          --label module=tcp_v4_online \
          --select="ndt.iupui.(${!pattern})" > \
              ${output}/blackbox-targets/ndt_raw.json

      # NDT SSL on port 3010.
      ./mlabconfig.py --format=prom-targets \
          --template_target={{hostname}}:3010 \
          --label service=ndt_ssl \
          --label module=tcp_v4_tls_online \
          --use_flatnames \
          --select="ndt.iupui.(${!pattern})" > \
              ${output}/blackbox-targets/ndt_ssl.json

      # Mobiperf on ports 6001, 6002, 6003.
      ./mlabconfig.py --format=prom-targets \
          --template_target={{hostname}}:6001 \
          --template_target={{hostname}}:6002 \
          --template_target={{hostname}}:6003 \
          --label service=mobiperf \
          --label module=tcp_v4_online \
          --select="1.michigan.(${!pattern})" > \
              ${output}/blackbox-targets/mobiperf.json

      # neubot on port 9773.
      ./mlabconfig.py --format=prom-targets \
          --template_target={{hostname}}:9773/sapi/state \
          --label service=neubot \
          --label module=neubot_online \
          --select="neubot.mlab.(${!pattern})" > \
              ${output}/blackbox-targets/neubot.json

      ########################################################################
      # Note: The following configs select all servers. This allows us to
      # experiment with monitoring many sites in sandbox or staging before
      # production.
      ########################################################################

      # snmp_exporter on port 9116.
      ./mlabconfig.py --format=prom-targets-sites \
          --template_target=s1.{{sitename}}.measurement-lab.org \
          --label service=snmp \
          --label __exporter_project=${project#mlab-} > \
              ${output}/snmp-targets/snmpexporter.json

      # inotify_exporter for NDT on port 9393.
      ./mlabconfig.py --format=prom-targets \
          --template_target={{hostname}}:9393 \
          --label service=inotify \
          --select="ndt.iupui.*" > \
              ${output}/legacy-targets/ndt_inotify.json

      # node_exporter on port 9100.
      ./mlabconfig.py --format=prom-targets-nodes \
          --template_target={{hostname}}:9100 \
          --label service=nodeexporter \
          --label module=lame_duck > \
              ${output}/legacy-targets/lameduck.json

    else
      echo "Unknown group name: ${GROUP} for ${project}"
    fi
  popd
done
