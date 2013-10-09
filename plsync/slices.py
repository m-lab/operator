#!/usr/bin/python

import pprint
from planetlab.types import *

# The CentOS build adds new functionality to slices through vsys capabilities
# for restart, update and yum configuration.  These attributes should be added
# to all slices on M-Lab.
centos_slice_attrs = [ Attr(None, vsys='slice_restart'),
                       Attr(None, vsys='slice_update'),
                       Attr(None, vsys='slice_yum'),
                       Attr('MeasurementLabCentos', isolate_loopback='1'),
                     ]

# NOTE: The arch, pldistro, and fcdistro slicetags apply GLOBALLY to slices.
#       And, while a NodeGroup assignment would ordinarily limit the scope of a
#       slicetag, for these, per-nodegroup values are ignored.
#       The default on public PlanetLab slices: 
#            arch=i386, pldistro=planetlab, fcdistro=f8.
#       M-Lab servers work around this limitation by creating a symlink from
#       /vservers/.vref/planetlab-f8-i386 -> /vservers/.vref/mlab-centos6-i386
#   Attr(None, arch='i386'),
#   Attr(None, pldistro='mlab'),
#   Attr(None, fcdistro='centos6'),

# NOTE: VXC_ENABLE_WEB100 is disabled by default.  To enable web100 statistics
#       collection add the VXC_ENABLE_WEB100 flag.
web100_enable_attr = [ Attr('MeasurementLabCentos', capabilities='vxc_^28') ]
initscript_attr    = [ ]

mlab4s_only = ['mlab4.nuq01', 'mlab4.nuq02', 'mlab4.prg01']

# name  : the slice name
# index : the index into the iplist for each node to assign to this slice
# attr  : a list of slice attributes.
# use_initscript : boolean, indicating to use 'mlab_generic_initscript'; for
#                  slices with installable packages, this should be True.
# ipv6  : how to assign ipv6 addresses to slices.  None=do not assign. Explicit
#         list of machine names, or "all" for all machines.
slice_list = [

    Slice(name='gt_partha',       index=0, attrs=centos_slice_attrs+web100_enable_attr, 
                                           use_initscript=True, 
                                           ipv6=mlab4s_only ),
    Slice(name='iupui_ndt',       index=1, attrs=centos_slice_attrs+web100_enable_attr+[
                                                Attr('MeasurementLabCentos',    disk_max='60000000') ], 
                                           use_initscript=True,
                                           ipv6=mlab4s_only ),
    Slice(name='iupui_npad',      index=2, attrs=centos_slice_attrs+web100_enable_attr+[
                                                Attr('MeasurementLabCentos',    disk_max='10000000'),
                                                Attr(None,    vsys='web100_proc_write'), ],
                                           use_initscript=True,
                                           ipv6="all"),
    Slice(name='mpisws_broadband',index=3, attrs=centos_slice_attrs+[
                                                Attr('MeasurementLabCentos', capabilities='CAP_NET_RAW,vxc_^28'),
                                                Attr('MeasurementLabCentos', disk_max='35000000'), ], 
                                           use_initscript=True,
                                           ipv6=mlab4s_only),
    #Slice(name="mlab_mitate",    index=4, attrs=centos_slice_attrs+web100_enable_attr, ipv6="all"),
    Slice(name="uw_geoloc4",      index=5, attrs=centos_slice_attrs+web100_enable_attr, ipv6=mlab4s_only),
    Slice(name="mlab_ooni",       index=6, attrs=centos_slice_attrs+[
                                                Attr(None,      capabilities='CAP_NET_BIND_SERVICE,CAP_NET_RAW') ], 
                                           ipv6="all"),
    Slice(name="samknows_ispmon", index=7, attrs=centos_slice_attrs+web100_enable_attr, ipv6=mlab4s_only),
    Slice(name="gt_bismark",      index=8, attrs=centos_slice_attrs+web100_enable_attr, ipv6=mlab4s_only),
    Slice(name="mlab_neubot",     index=9, attrs=centos_slice_attrs+[
                                                Attr('MeasurementLabCentos', capabilities='CAP_NET_BIND_SERVICE,vxc_^28'), ], 
                                           use_initscript=True,
                                           ipv6="all"),
    Slice(name="michigan_1",      index=10, attrs=centos_slice_attrs+web100_enable_attr, 
                                           use_initscript=True,
                                           ipv6="all"),

    Slice(name='mlab_utility',    index=11, attrs=centos_slice_attrs+[
                                                Attr('MeasurementLabCentos', capabilities='CAP_NET_BIND_SERVICE,vxc_^28'), ],
                                            use_initscript=True,
                                            ipv6="all"),

    Slice(name="pl_netflow"),

    # NOTE: The 'pl_default' slice is treated specially.  This slice assigns default
    #       settings to the servers to which it is assigned.  For M-Lab:
    #           'codemux=-1' disables the service that binds to port 80.
    #           'net_max_rate=-1' disables network rate limiting for all slices.
    Slice(name="pl_default", attrs=centos_slice_attrs+[Attr('MeasurementLabCentos', codemux='-1'),
                                                       Attr('MeasurementLabCentos', net_max_rate='-1'),])
]
