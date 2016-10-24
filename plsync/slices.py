#!/usr/bin/python

import pprint
from planetlab.model import *
from users import user_list
# NOTE: slice attributes:
# All slice attributes are key=value pairs.  Values are always specified as a
# string, even when they are interpreted later as integers.
# The first argument of an Attr() object is the context.  "None" means no
# context, so it applies everywhere. Alternate options are a NodeGroup name, or
# a hostname.
# Examples:
#    Attr(None, enabled='0')
#    Attr('MeasurementLabCentos', enabled='0')
#    Attr("mlab4.nuq01.measurement-lab.org', enabled='0')

# NOTE: The CentOS build adds new functionality to slices through vsys scripts for
# restart, update and yum configuration.  These slice attributes should be added
# to all slices on M-Lab. There is a bug in vsys or nodemanager that fails to
# apply vsys scripts conditionally based on NodeGroup, so all vsys scripts
# should be specified with nodegroup "None".
centos_slice_attrs =  [ Attr(None, vsys='slice_restart'),
                        Attr(None, vsys='slice_update'),
                        Attr(None, vsys='slice_yum'), ]

# NOTE: The isolate_loopback attribute enforces that localhost (127.0.0.1) in a
# vserver is not shared across vservers.  loopback sharing is the default.  This
# setting must be applied *before* the slice is created on the node.  If applied
# afterward, the slice must be destroyed and recreated with 'slice-update'
centos_slice_attrs += [ Attr('MeasurementLabCentos', isolate_loopback='1') ]

# NOTE: The arch, pldistro, and fcdistro slicetags apply GLOBALLY to slices.
# And, while a NodeGroup assignment would ordinarily limit the scope of a
# slicetag, for these tags, per-nodegroup values are ignored.  The default on
# public PlanetLab slices is always: arch=i386, pldistro=planetlab, fcdistro=f8.
#       
# M-Lab servers create reference filesystems based on CentOS 6 of course.
# However, as far as NodeManager is concerned, it will try to create f8 vms.
# M-Lab servers work around this limitation by creating a symlink from
# /vservers/.vref/planetlab-f8-i386 -> /vservers/.vref/mlab-centos6-i386
# 
# NOTE: On boot-test.measurementlab.net, slices *should* include these tags for the
# CentOS machines.  For the LXC machines, they *should not* include these tags.
#centos_slice_attrs += [ Attr(None, arch='i386'), 
#                        Attr(None, pldistro='mlab'), 
#                        Attr(None, fcdistro='centos6'), ]

# NOTE: slice capabilities are all disabled by default.  Some slices need
# additional privileges to run their experiments or bind to privileged ports. 
# New capabilities are:
#   VXC_ENABLE_WEB100 - enable web100 statistics collection. The symbol "vxc_" 
#       is a prefix that indicates a vserver capability. The ^28 indicates that
#       the 28th bit is set high.  Normally vserver capabilities have canonical
#       names. Since this is a custom one, it is not supported by vserver-utils
# Linux Capabilities:
#   http://man7.org/linux/man-pages/man7/capabilities.7.html
# VServer configuration hints: 
#   http://www.nongnu.org/util-vserver/doc/conf/configuration.html
web100_enable_attr = [ Attr('MeasurementLabCentos', capabilities='vxc_^28') ]


mlab4s_only = ['mlab4.nuq01', 'mlab4.nuq02', 'mlab4.prg01', 
               'mlab1.nuq0t', 'mlab2.nuq0t', 'mlab3.nuq0t', 'mlab4.nuq0t']

# name  : the slice name (expected to exist in planetlab database already)
# index : the index into the iplist for each node to assign to this slice.
#         M-Lab has 12 slots, numbered from 0 to 11.
#         NOTE: While it is possible for multiple slices to share an index,
#         (and thus their IPs), it is not possible from inside one vm to see
#         what ports are occupied by the other vm. Connection attempts to bind
#         just fail.
# attr  : a list of slice attributes.
# users : a list of users to add to the slice.  this is supported primarily
#         to allow non-admin users to generate dns information by collecting the
#         slice attributes of configured slices.
# use_initscript : boolean, indicating to use 'mlab_generic_initscript'; for
#                  slices with installable packages, this should be True.
#                  Unsetting this attribute is manual. TODO: allow specifying
#                  arbitrary initscripts and support resetting.
# ipv6  : specifies how to assign ipv6 addresses to slices. Accepted values are:
#            None - do not assign.
#            list - An explicit list of machine names to permit ipv6 addresses
#            "all" - assign ipv6 addresses to all machines
#         If a site lacks IPv6 addresses, none will be assigned even if "all" is
#         given. For example, see lca01+npad.
slice_list = [

    Slice(name='iupui_ndt',       index=1, attrs=centos_slice_attrs+[
                                                Attr('MeasurementLabCentos',    disk_max='100000000'),  # 100GB.
                                                Attr('MeasurementLabCentos', capabilities='CAP_NET_BIND_SERVICE,vxc_^28'), ], 
                                           users=user_list,
                                           use_initscript=True,
                                           ipv6=['mlab1.nuq0t', 'mlab2.nuq0t', 'mlab3.nuq0t', 'mlab4.nuq0t',
                                                 'mlab1.nuq1t', 'mlab2.nuq1t', 'mlab3.nuq1t', 'mlab4.nuq1t',
                                                 'mlab1.iad0t', 'mlab2.iad0t', 'mlab3.iad0t', 'mlab4.iad0t',
                                                 'mlab1.iad1t', 'mlab2.iad1t', 'mlab3.iad1t', 'mlab4.iad1t',]),
    Slice(name='iupui_npad',      index=2, attrs=centos_slice_attrs+web100_enable_attr+[
                                                Attr('MeasurementLabCentos',    disk_max='10000000'),
                                                Attr(None,    vsys='web100_proc_write'), ],
                                           users=user_list,
                                           use_initscript=True,
                                           ipv6="all"),
    Slice(name='mpisws_broadband',index=3, attrs=centos_slice_attrs+[
                                                Attr('MeasurementLabCentos', capabilities='CAP_NET_RAW,vxc_^28'),
                                                Attr('MeasurementLabCentos', disk_max='35000000'), ], 
                                           users=user_list,
                                           use_initscript=True,
                                           ipv6=mlab4s_only),
    #Slice(name="mlab_mitate",    index=4, attrs=centos_slice_attrs+web100_enable_attr, users=user_list, ipv6="all"),
    Slice(name="uw_geoloc4",      index=5, attrs=centos_slice_attrs+web100_enable_attr, 
                                           users=user_list,
                                           ipv6=mlab4s_only + ['mlab4.ath03', 'mlab4.mnl01', 'mlab4.nuq1t', 'mlab4.dfw02']),
    Slice(name="mlab_ooni",       index=6, attrs=centos_slice_attrs+[
                                                #Attr(None,      capabilities='CAP_NET_BIND_SERVICE,CAP_NET_RAW') ], 
                                                Attr('MeasurementLabCentos', capabilities='CAP_NET_BIND_SERVICE,CAP_NET_RAW') ], 
                                           users=user_list,
                                           use_initscript=True,
                                           ipv6="all"),
    Slice(name="samknows_ispmon", index=7, attrs=centos_slice_attrs+web100_enable_attr,
                                           users=user_list,
                                           ipv6="all"),
    Slice(name="gt_bismark",      index=8, attrs=centos_slice_attrs+[
                                                Attr('MeasurementLabCentos', capabilities='CAP_NET_BIND_SERVICE,vxc_^28'), ], 
                                           users=user_list,
                                           ipv6=mlab4s_only),
    Slice(name="mlab_neubot",     index=9, attrs=centos_slice_attrs+[
                                                Attr('MeasurementLabCentos', capabilities='CAP_NET_BIND_SERVICE,vxc_^28'), ], 
                                           users=user_list,
                                           use_initscript=True,
                                           ipv6="all"),
    Slice(name="michigan_1",      index=10, attrs=centos_slice_attrs+web100_enable_attr, 
                                           users=user_list,
                                           use_initscript=True,
                                           ipv6="all"),

    Slice(name='mlab_utility',    index=11, attrs=centos_slice_attrs+[
                                                Attr('MeasurementLabCentos', capabilities='CAP_NET_BIND_SERVICE,vxc_^28'), 
                                                Attr(None, vsys='vs_resource_backend') ],
                                            users=user_list,
                                            use_initscript=True,
                                            ipv6="all"),

    Slice(name="pl_netflow"),

    # NOTE: The 'pl_default' slice is treated specially by NodeManager.  This
    # slice assigns default settings to the servers to which it is assigned.
    # For M-Lab:
    #   'codemux=-1' disables the service that binds to port 80.
    #   'net_max_rate=-1' disables network rate limiting for all slices.
    Slice(name="pl_default", attrs=centos_slice_attrs+[Attr('MeasurementLabCentos', codemux='-1'),
                                                       Attr('MeasurementLabCentos', net_max_rate='-1'),])
]
