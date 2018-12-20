#!/bin/bash


# Root directory of this script.
SCRIPTDIR=$( dirname "${BASH_SOURCE[0]}" )
BASEDIR=${PWD}

USAGE="Usage: $0 <GROUP>"
GROUP=${1:?Please provide monitoring group name: $USAGE}

# Create all output directories.
for project in mlab-sandbox mlab-staging mlab-oti ; do
  mkdir -p ${BASEDIR}/gen/${project}/prometheus/{legacy-targets,blackbox-targets,blackbox-targets-ipv6,snmp-targets,script-targets}
done

# All testing sites and machines.
SELECT_mlab_sandbox=$( cat ${SCRIPTDIR}/plsync/testing_patterns.txt | xargs | sed -e 's/ /|/g' )

# All mlab4's and the set of canary machines.
SELECT_mlab_staging=$( cat ${SCRIPTDIR}/plsync/staging_patterns.txt ${SCRIPTDIR}/plsync/canary_machines.txt | xargs | sed -e 's/ /|/g' )

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

    if [[ ${GROUP} == scraper ]] ; then
      # Rsyncd on port 7999.
      ./mlabconfig.py --format=prom-targets \
          --template_target={{hostname}}:7999 \
          --label service=rsyncd \
          --label module=rsyncd_online \
          --rsync \
          --select "${!pattern}" > ${output}/blackbox-targets/rsyncd.json

      # SSH on port 806 over IPv4
      ./mlabconfig.py --format=prom-targets-nodes \
          --template_target={{hostname}}:806 \
          --label service=ssh806 \
          --label module=ssh_v4_online \
          --select "${!pattern}" > ${output}/blackbox-targets/ssh806.json

      # SSH on port 806 over IPv6
      ./mlabconfig.py --format=prom-targets-nodes \
          --template_target={{hostname}}:806 \
          --label service=ssh806 \
          --label module=ssh_v6_online \
          --label __blackbox_port=${!bbe_port} \
          --select "${!pattern}" \
          --decoration "v6" > ${output}/blackbox-targets-ipv6/ssh806_ipv6.json

      # Sidestream exporter in the npad experiment.
      ./mlabconfig.py --format=prom-targets \
          --template_target={{hostname}}:9090 \
          --label service=sidestream \
          --select "npad.iupui.(${!pattern})" > \
              ${output}/legacy-targets/sidestream.json

    elif [[ ${GROUP} == global ]] ; then

      ########################################################################
      # Note: The following configs select all servers. This allows us to
      # experiment with monitoring many sites in sandbox or staging before
      # production.
      ########################################################################

      # NDT "raw" on port 3001 over IPv4
      ./mlabconfig.py --format=prom-targets \
          --template_target={{hostname}}:3001 \
          --label service=ndt_raw \
          --label module=tcp_v4_online \
          --select "ndt.iupui.(${!pattern})" > \
              ${output}/blackbox-targets/ndt_raw.json

      # NDT "raw" on port 3001 over IPv6
      ./mlabconfig.py --format=prom-targets \
          --template_target={{hostname}}:3001 \
          --label service=ndt_raw_ipv6 \
          --label module=tcp_v6_online \
          --label __blackbox_port=${!bbe_port} \
          --select "ndt.iupui.(${!pattern})" \
          --decoration "v6" > \
              ${output}/blackbox-targets-ipv6/ndt_raw_ipv6.json

      # NDT SSL on port 3010 over IPv4
      ./mlabconfig.py --format=prom-targets \
          --template_target={{hostname}}:3010 \
          --label service=ndt_ssl \
          --label module=tcp_v4_tls_online \
          --use_flatnames \
          --select "ndt.iupui.(${!pattern})" > \
              ${output}/blackbox-targets/ndt_ssl.json

      # NDT SSL on port 3010 over IPv6
      ./mlabconfig.py --format=prom-targets \
          --template_target={{hostname}}:3010 \
          --label service=ndt_ssl_ipv6 \
          --label module=tcp_v6_tls_online \
          --label __blackbox_port=${!bbe_port} \
          --use_flatnames \
          --select "ndt.iupui.(${!pattern})" \
          --decoration "v6" > \
              ${output}/blackbox-targets-ipv6/ndt_ssl_ipv6.json

      # script_exporter for NDT end-to-end monitoring
      ./mlabconfig.py --format=prom-targets \
          --template_target={{hostname}} \
          --label service=ndt_e2e \
          --use_flatnames \
          --select "ndt.iupui.(${!pattern})" > \
              ${output}/script-targets/ndt_e2e.json

      # script_exporter for NDT queueing check
      ./mlabconfig.py --format=prom-targets \
          --template_target={{hostname}} \
          --label service=ndt_queue \
          --use_flatnames \
          --select "ndt.iupui.(${!pattern})" > \
              ${output}/script-targets/ndt_queue.json

      # Mobiperf on ports 6001, 6002, 6003 over IPv4.
      ./mlabconfig.py --format=prom-targets \
          --template_target={{hostname}}:6001 \
          --template_target={{hostname}}:6002 \
          --template_target={{hostname}}:6003 \
          --label service=mobiperf \
          --label module=tcp_v4_online \
          --select "1.michigan.(${!pattern})" > \
              ${output}/blackbox-targets/mobiperf.json

      # Mobiperf on ports 6001, 6002, 6003 over IPv6.
      ./mlabconfig.py --format=prom-targets \
          --template_target={{hostname}}:6001 \
          --template_target={{hostname}}:6002 \
          --template_target={{hostname}}:6003 \
          --label service=mobiperf_ipv6 \
          --label module=tcp_v6_online \
          --label __blackbox_port=${!bbe_port} \
          --select "1.michigan.(${!pattern})" \
          --decoration "v6" > ${output}/blackbox-targets-ipv6/mobiperf_ipv6.json

      # neubot on port 9773 over IPv4.
      ./mlabconfig.py --format=prom-targets \
          --template_target={{hostname}}:9773/sapi/state \
          --label service=neubot \
          --label module=neubot_online_v4 \
          --select "neubot.mlab.(${!pattern})" > \
              ${output}/blackbox-targets/neubot.json

      # neubot on port 9773 over IPv6.
      ./mlabconfig.py --format=prom-targets \
          --template_target={{hostname}}:9773/sapi/state \
          --label service=neubot_ipv6 \
          --label module=neubot_online_v6 \
          --label __blackbox_port=${!bbe_port} \
          --select "neubot.mlab.(${!pattern})" \
          --decoration "v6" > ${output}/blackbox-targets-ipv6/neubot_ipv6.json

      # snmp_exporter on port 9116.
      ./mlabconfig.py --format=prom-targets-sites \
          --template_target=s1.{{sitename}}.measurement-lab.org \
          --label service=snmp > \
              ${output}/snmp-targets/snmpexporter.json

      # inotify_exporter for NDT on port 9393.
      ./mlabconfig.py --format=prom-targets \
          --template_target={{hostname}}:9393 \
          --label service=inotify \
          --select "ndt.iupui.(${!pattern})" > \
              ${output}/legacy-targets/ndt_inotify.json

      # node_exporter on port 9100.
      ./mlabconfig.py --format=prom-targets-nodes \
          --template_target={{hostname}}:9100 \
          --label service=nodeexporter \
          --select "${!pattern}" > \
              ${output}/legacy-targets/nodeexporter.json

      # ICMP probe for platform switches
      ./mlabconfig.py --format=prom-targets-sites \
          --template_target=s1.{{sitename}}.measurement-lab.org \
          --label module=icmp > \
              ${output}/blackbox-targets/switches_ping.json

      # SSH on port 22 over IPv4
      ./mlabconfig.py --format=prom-targets-nodes \
          --template_target={{hostname}}:22 \
          --label service=ssh \
          --label module=ssh_v4_online \
          --select "${!pattern}" > ${output}/blackbox-targets/ssh.json

      # SSH on port 22 over IPv6
      ./mlabconfig.py --format=prom-targets-nodes \
          --template_target={{hostname}}:22 \
          --label service=ssh \
          --label module=ssh_v6_online \
          --label __blackbox_port=${!bbe_port} \
          --select "${!pattern}" \
          --decoration "v6" > ${output}/blackbox-targets-ipv6/ssh_ipv6.json

    else
      echo "Unknown group name: ${GROUP} for ${project}"
    fi
  popd
done
