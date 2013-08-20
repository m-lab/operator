#!/usr/bin/python

import pprint
from sync import *
import session

def breakdown(host_index, v4prefix):
    octet_list = v4prefix.split('.')
    assert(len(octet_list) == 4)
    net_prefix = ".".join(octet_list[0:3])
    net_offset = int(octet_list[3])
    mlab_offset = net_offset + ((host_index - 1) * 13) + 9
    return (net_prefix, net_offset, mlab_offset)

def pl_interface(host_index, v4prefix):
    (net_prefix, net_offset, mlab_offset) = breakdown(host_index, v4prefix)
    interface={}
    interface['type']       = 'ipv4'
    interface['method']     = 'static'
    interface['network']    = v4prefix
    interface['dns1']       = '8.8.8.8'
    interface['dns2']       = '8.8.4.4'
    interface['netmask']    = '255.255.255.192'
    interface['is_primary'] = True
    interface['gateway']    = '%s.%d' % (net_prefix, net_offset + 1)
    interface['broadcast']  = '%s.%d' % (net_prefix, net_offset + 63)
    interface['ip']         = '%s.%d' % (net_prefix, mlab_offset)
    return interface

def pl_v6_iplist(host_index, v6prefix, last_octet):
    mlab_offset = last_octet + ((host_index - 1) * 13) + 9
    ret = []
    for ip in range(mlab_offset + 1, mlab_offset + 13):
        ret.append(v6prefix+str(ip))
    return ret

def pl_v6_primary(host_index, v6prefix, last_octet):
    mlab_offset = last_octet + ((host_index - 1) * 13) + 9
    return v6prefix+str(mlab_offset)

def pl_iplist(host_index, v4prefix):
    (net_prefix, net_offset, mlab_offset) = breakdown(host_index, v4prefix)
    ret = [] 
    for ip in range(mlab_offset + 1, mlab_offset + 13):
        ret.append('%s.%s' % (net_prefix,ip))
    return ret

def pl_dracip(host_index, v4prefix):
    (net_prefix, net_offset, mlab_offset) = breakdown(host_index, v4prefix)
    return '%s.%d' % (net_prefix, net_offset+3+host_index)

def pl_v6gw(v6prefix, v6gw=None):
    return v6prefix + "1" if v6gw is None else v6gw

class Location(dict):
    def __init__(self, city, country, lat, lon, **kwargs):
        self['city'] = city
        self['country'] = country
        self['latitude'] = lat
        self['longitude'] = lon
        super(Location, self).__init__(**kwargs)

class Network(dict):
    """The Network() object encapsulates the IP and network objects for the IPv4
    and IPv6 settings for an M-Lab site.  

    Network() constructor expects two parameters:
        v4 - string, a /26 IPv4 prefix i.e. 192.168.10.0
        v6 - string, a /64 IPv6 prefix i.e. 2604:ca00:f000::
        v6gw - optional, string, a specific gateway other than the 
               default, <prefix>::1

    Attributes:
        Network['v4'] is a NetworkIPv4() object
        Network['v6'] is a NetworkIPv6() object
    """
    legacy_network_remap = None
    def __str__(self):
        return pprint.pformat(self)
    def __init__(self, **kwargs):
        if 'v4' not in kwargs:
            raise Exception("'v4' is a mandatory argument. i.e. 64.9.225.128")
        if 'v6' not in kwargs:
            msg = "'v6' is a mandatory argument. i.e. 2604:ca00:f000::"
            raise Exception(msg)
        if 'v6gw' not in kwargs:
            kwargs['v6gw'] = None

        kwargs['v4'] = NetworkIPv4(prefix=kwargs['v4'])
        # Allow disabling IPv6
        if kwargs['v6'] is not None:
            kwargs['v6'] = NetworkIPv6(prefix=kwargs['v6'],
                                       last_octet=kwargs['v4'].last(), 
                                       v6gw=kwargs['v6gw'])

        super(Network, self).__init__(**kwargs)

class NetworkIPv6(dict):
    """The NetworkIPv6() object encapsulates operations for IPv6 network
    configuration on M-Lab sites and nodes.  It has built-in methods for
    extracting per-node attributes and managing IP assignment to slices.

    NetworkIPv6() constructor expects these parameters:
        prefix - string, a /64 IPv6 prefix i.e. 2604:ca00:f000::
        last_octet - string the last octet of the IPv4 site prefix. This
                    value is used to offset all addresses.  Should be one of 0,
                    64, 128, or 192.
        v6gw - a specific gateway, if None, defaults to <prefix>::1
    """
    def __str__(self):
        return pprint.pformat(self)
    def __init__(self, **kwargs):
        if 'prefix' not in kwargs:
            msg = "'prefix' is a mandatory argument. i.e. 2604:ca00:f000::"
            raise Exception(msg)
        if 'last_octet' not in kwargs:
            msg ="'last_octet' is a mandatory argument. i.e. if v4 "
            msg+="prefix is 192.168.10.64 then last_octet is 64"
            raise Exception(msg)
        if 'v6gw' not in kwargs:
            raise Exception("'v6gw' is a mandatory argument. Can be None.")

        super(NetworkIPv6, self).__init__(**kwargs)

    def ipv6_defaultgw(self):
        """ Returns the IPv6 gateway as calculated from prefix & v6gw """
        return pl_v6gw(self['prefix'], self['v6gw'])

    def ipv6addr(self, host_index):
        """ Returns the host IPv6 address for the host_index node; host_index
        should be less than 4, the maximum number of nodes at a site."""
        return pl_v6_primary(host_index, self['prefix'], 
                             int(self['last_octet']))

    def ipv6addr_secondaries(self, index):
        """ Returns a list of 12 IPv6 addresses assigned to given host_index """
        # NOTE: the natural, sorted order is re-ordered according to 
        #       legacy_network_remap if present.
        ipv6_list = pl_v6_iplist(index, self['prefix'], int(self['last_octet']))
        if ( Network.legacy_network_remap is not None and 
             self['name'] in Network.legacy_network_remap and
             index in Network.legacy_network_remap[self['name']] ):

            site = self['name']
            index_list = Network.legacy_network_remap[site][index].split(",")
            re_order = [ ipv6_list[int(i)] for i in index_list ]
            return re_order
            
        return ipv6_list

class NetworkIPv4(dict):
    """The NetworkIPv4() object encapsulates the IP and network settings for an
    M-Lab site.  It has built-in methods for extracting per-node attributes and
    managing IP assignment to slices.

    NetworkIPv4() constructor expects these parameters:
        prefix - string, a /26 IPv4 prefix i.e. 192.168.10.0
    """
    def __str__(self):
        return pprint.pformat(self)
    def __init__(self, **kwargs):
        if 'prefix' not in kwargs:
            msg="'prefix' is a mandatory argument. i.e.  192.168.10.0"
            raise Exception(msg)
        super(NetworkIPv4, self).__init__(**kwargs)

    def interface(self, index):
        """ Returns the myPLC interface definition for the given host index"""
        return pl_interface(index, self['prefix'])

    def iplist(self, index):
        """ Returns a list of 12 IPv4 addresses for the given host index """
        ip_list = pl_iplist(index, self['prefix'])
        if (Network.legacy_network_remap is not None and 
            self['name'] in Network.legacy_network_remap and
            index in Network.legacy_network_remap[self['name']] ):
            site = self['name']
            index_list = Network.legacy_network_remap[site][index].split(",")

            re_order = [ ip_list[int(i)] for i in index_list ]
            return re_order
        return ip_list 

    def drac(self, index):
        """ Returns the IPv4 address reserved for the DRAC interface"""
        return pl_dracip(index, self['prefix'])

    def last(self):
        """ Returns the last octet of 'prefix' """
        l = self['prefix'].split('.')[3]
        return int(l)

class Site(dict):
    """Site() - represents an M-Lab site.  Also wraps the creation of site 
        Node()s and PCU()s.

       Site() constructor expects:
            name - a short name for a site, i.e. nuq01
            net  - a Network() object consisting of at least an IPv4 prefix

          Optional:
            count - the number of nodes at the site (default: 3)
            nodegroup - the nodegroup with which to associate new nodes at 
                        this site.  (default: MeasurementLab)
            pi - a list of people to add as PI's for a new site.
                 (default: Stephen Stuart)
            login_base_prefix - a constant prefix for to prepend to 'name' 
                                (default: mlab).

    """
    def __str__(self):
        return pprint.pformat(self)

    def __init__(self, **kwargs):
        if 'name' not in kwargs:
            raise Exception("'name' is a mandatory argument. i.e. nuq01, lga02")
        if 'net' not in kwargs:
            raise Exception("'net' is a mandatory argument.")

        if 'count' not in kwargs:
            kwargs['count'] = 3
        if 'nodegroup' not in kwargs:
            kwargs['nodegroup'] = 'MeasurementLab'
        if 'pi' not in kwargs:
            kwargs['pi'] = [ ("Stephen","Stuart","sstuart@google.com") ]
        if 'login_base_prefix' not in kwargs:
            kwargs['login_base_prefix'] = 'mlab'
        if 'location' not in kwargs:
            kwargs['location'] = None

        if kwargs['net'] is not None:
            if kwargs['net']['v4'] is not None:
                kwargs['net']['v4']['name'] = kwargs['name']
            if kwargs['net']['v6'] is not None:
                kwargs['net']['v6']['name'] = kwargs['name']
        else:
            # 'net' is None only if there are no nodes for this site
            assert(kwargs['count'] == 0)

        if 'login_base' not in kwargs:
            kwargs['login_base'] = '%s%s' % (kwargs['login_base_prefix'],
                                             kwargs['name'])
        kwargs['sitename'] = 'MLab - %s' % kwargs['name'].upper()

        if 'nodes' not in kwargs:
            kwargs['nodes'] = {}

            for i in range(1,kwargs['count']+1):
                p = PCU(name=kwargs['name'], index=i, net=kwargs['net'])
                exclude_ipv6=True
                if ( 'exclude' not in kwargs or 
                    ('exclude' in     kwargs and i not in kwargs['exclude'])
                   ):
                    exclude_ipv6=False
                n = Node(name=kwargs['name'], index=i, net=kwargs['net'], 
                         pcu=p, nodegroup=kwargs['nodegroup'],
                         exclude_ipv6=exclude_ipv6,
                         login_base=kwargs['login_base'])
                kwargs['nodes'][n.hostname()] = n

        super(Site, self).__init__(**kwargs)

    def sync(self, onhost=None, skipinterfaces=False, getbootimages=False):
        """ Do whatever is necessary to validate this site in the myplc DB.
            Actions may include creating a new Site() entry in myPLC DB, 
            creating people listed as PIs, creating nodes and PCUs.  
        """
        MakeSite(self['login_base'], self['sitename'], self['sitename'])
        SyncLocation(self['login_base'], self['location'])
        for person in self['pi']:
            p_id = MakePerson(*person)
            email = person[2]
            AddPersonToSite(email,p_id,"tech",self['login_base'])
            AddPersonToSite(email,p_id,"pi",self['login_base'])
        for hostname,node in self['nodes'].iteritems():
            if onhost is None or hostname == onhost:
                node.sync(skipinterfaces, getbootimages)

def makesite(name, v4prefix, v6prefix, city, country, 
             latitude, longitude, pi_list, **kwargs):
    v6gw=None               # use default
    if 'v6gw' in kwargs:    # but, if provided
        v6gw=kwargs['v6gw'] # save for Network() object below
        del kwargs['v6gw']  # and don't pass to Site()
    location=None
    if city is not None:
        # NOTE: only create Location() if city* is specified.
        location = Location(city, country, latitude, longitude)
    return Site(name=name, 
                net=Network(v4=v4prefix, v6=v6prefix, v6gw=v6gw),
                location=location,
                pi=pi_list,
                **kwargs)

class PCU(dict):
    """ PCU() - represents an M-Lab PCU at a parent Site()

    PCU() constructor expects:
        name - the site name, i.e. nuq01
        net - the NetworkIPv4() object representing the parent site.
        index - the host index for the machine this PCU is associated with.

      Optional:
        username - drac username (default: admin)
        password - drac password (default: changeme)
        model    - drac model (default: DRAC)
    """
    def __str__(self):
        #return pprint.pformat(self)
        return self.fields()
    def __init__(self, **kwargs):
        if 'name' not in kwargs:
            raise Exception("'name' is a mandatory argument. i.e. nuq01")
        if 'net' not in kwargs:
            raise Exception("'net' is a mandatory argument.")
        if 'index' not in kwargs:
            raise Exception("'index' is a mandatory argument. i.e. 1,2,3")

        if 'username' not in kwargs:
            kwargs['username'] = 'admin'
        if 'password' not in kwargs:
            kwargs['password'] = 'changeme'
        if 'model' not in kwargs:
            kwargs['model'] = 'DRAC'
        super(PCU, self).__init__(**kwargs)

    def hostname(self):
        """ generate the hostname for this DRAC based on index & site name """
        return "mlab%dd.%s.measurement-lab.org" % (self['index'], self['name'])

    def fields(self):
        """ return a dict() with the PCU values for use by myplc AddPCU() """
        return { 'username': self['username'],
                 'password': self["password"],      # password is updated later.
                 'model'   : self['model'],
                 'ip'      : self['net']['v4'].drac(self['index']),
                 'hostname': self.hostname() }
        
class Node(dict):
    """ Node() - represents an M-Lab node at a parent Site().
    Node() constructor expects these parameters:
        name - the site name, i.e. nuq01
        index - the host index for the machine this PCU is associated with.
        net - the Network() object representing the parent site, will contain
                both ipv4 & ipv6 information (if present).
        exclude_ipv6 - whether or not to exclude ipv6 from the configuration
    """
    def __str__(self):
        return str({ 'interface' : self.interface(),
                     'iplist'    : self.iplist(),
                     'iplistv6'  : self.iplistv6(), 
                     'pcu'       : self['pcu'].fields()})
    def __init__(self, **kwargs):
        if 'name' not in kwargs:
            raise Exception("'name' is a mandatory argument. i.e. FQDN")
        if 'index' not in kwargs:
            raise Exception("'index' is a mandatory argument. i.e. 1,2,3")
        if 'net' not in kwargs:
            raise Exception("'net' is a mandatory argument.")
        if 'exclude_ipv6' not in kwargs:
            raise Exception("'exclude_ipv6' is a mandatory argument.")

        if 'login_base' not in kwargs:
            kwargs['login_base'] = 'mlab%s' % kwargs['name']
        kwargs['slicelist'] = []
        kwargs['ipv6_secondary'] = []
        super(Node, self).__init__(**kwargs)

    def interface(self):
        return self['net']['v4'].interface(self['index'])
    def iplist(self):
        return self['net']['v4'].iplist(self['index'])
    def iplistv6(self):
        return self['net']['v6'].ipv6addr_secondaries(self['index'])
    def v4gw(self):
        return self['net']['v4'].interface(self['index'])['gateway']
    def v6gw(self):
        return self['net']['v6'].ipv6_defaultgw()

    def hostname(self):
        return "mlab%d.%s.measurement-lab.org"  % (self['index'], self['name'])

    def v6interface_tags(self):
        secondary_list = self['net']['v6'].ipv6addr_secondaries(self['index'])
        goal = {
            "ipv6_defaultgw"       : self['net']['v6'].ipv6_defaultgw(),
            "ipv6addr"             : self['net']['v6'].ipv6addr(self['index']),
            "ipv6addr_secondaries" : " ".join(secondary_list)
        }
        # TODO: secondaries should be added after slices with ipv6 addresses
        # are added, right?
        return goal

    def addslice(self, slicename):
        if slicename not in self['slicelist']:
            self['slicelist'].append(slicename)

    def ipv6_is_enabled(self):
        return (self['net'] is not None and self['net']['v6'] is not None)

    def get_interface_attr(self, slice_obj):
        """ Used to construct the Interface() object for this node in myplc """
        attr = None
        if slice_obj['index'] is None:
            return None

        ip_index = int(slice_obj['index'])
        v4ip=self.iplist()[ip_index]
        v4gw=self.v4gw()

        v6ip=""
        v6gw=""
        ip_addresses = v4ip

        # update values when the node and the slice have ipv6 enabled
        if ( self.ipv6_is_enabled() and
             slice_obj.ipv6_is_enabled(self.hostname())):
            v6ip=self.iplistv6()[ip_index]
            v6gw=self.v6gw()
            ip_addresses = v4ip + "," + v6ip

        if self['nodegroup'] in ['MeasurementLabLXC']:
            ipv6_is_enabled = slice_obj.ipv6_is_enabled(self.hostname()) 
            ipv6init = "yes" if ipv6_is_enabled else "no"
            attr = Attr(self.hostname(),
                        interface=repr({'bridge':'public0',
                                        'DEVICE':'eth0',
                                        'BOOTPROTO':'static',
                                        'ONBOOT':'yes',
                                        'DNS1' : '8.8.8.8',
                                        'DNS2' : '8.8.4.4',
                                        'PRIMARY' : 'yes',
                                        'NETMASK' : '255.255.255.192',
                                        'IPADDR'  : v4ip,
                                        'GATEWAY' : v4gw,
                                        'IPV6INIT' : ipv6init,
                                        'IPV6ADDR' : v6ip,
                                        'IPV6_DEFAULTGW' : v6gw,}))

        elif self['nodegroup'] in ['MeasurementLab', 'MeasurementLabK32', 
                                   'MeasurementLabCentos']:
            attr = Attr(self.hostname(), ip_addresses=ip_addresses)
        else:
            raise Exception("unknown nodegroup: %s" % self['nodegroup'])

        return attr

    def sync(self, skipinterfaces=False, getbootimages=False):
        """Create and or verify that Node object & PCU & interface is created in
        myplc db"""

        node_id = MakeNode(self['login_base'], self.hostname())
        MakePCU(self['login_base'], node_id, self['pcu'].fields())
        PutNodeInNodegroup(self.hostname(), node_id, self['nodegroup'])
        interface = self.interface()
        if not skipinterfaces:
            SyncInterface(self.hostname(), node_id, interface,
                          interface['is_primary'])
            if self['nodegroup'] == 'MeasurementLabLXC':
                # NOTE: these tags are needed on the primary interface 
                #       for the lxc build of PlanetLab
                goal = { "ifname" : "eth0", "ovs_bridge": "public0"}
                SyncInterfaceTags(node_id, interface, goal)

        if not self['exclude_ipv6']:
            SyncInterfaceTags(node_id, interface, self.v6interface_tags())

        if not skipinterfaces and self['nodegroup'] != 'MeasurementLabLXC':
            for ip in self.iplist():
                interface['ip'] = ip
                interface['is_primary'] = False
                SyncInterface(self.hostname(), node_id, interface, 
                              interface['is_primary'])
        if getbootimages:
            GetBootimage(self.hostname(), imagetype="iso")
            
        return 

class Attr(dict):
    """Attr() are attributes of a slice, i.e. a key=value pair.
    
    Slice attributes apply key=value pairs to some context. Possible contexts
    are 'all nodes', 'only a specific node', 'only a specific nodegroup'.

    Attr() constructor expects one argument, and a key=value pair.
        arg[0] - the context for this slice attribute; may be one of: 
                 None - which represents all hosts
                 <hostname> - a hostname recognized by having a '.'
                 <nodegroup> - a nodegroup name, recognized by not having a '.'
        key=value - the key and value are not arbitrary.  The key must be one 
                 of a pre-defined set of recognized keys defined by the 
                 PlanetLab api.  The value for a given key, should be a valid 
                 value. Though, no type checking is performed here.
    """
    def __init__(self, *args, **kwargs):
        if len(args) != 1:
            raise Exception(("The first argument should be the name "+
                             "of a NodeGroup, hostname, or None"))

        if type(args[0]) == type(None):
            kwargs['attrtype'] = 'all'
            kwargs['all'] = True

        if type(args[0]) == str:
            if '.' in args[0]: 
                kwargs['attrtype'] = 'hostname'
                kwargs['hostname'] = args[0]
            else:
                kwargs['attrtype'] = 'nodegroup'
                kwargs['nodegroup'] = args[0]

        super(Attr, self).__init__(**kwargs)

class Slice(dict):
    """ Slice() - represents an M-Lab slice.  Provides an interface for passing
        additional slice attributes, and associating IP addresses. 

    Slice() constructor expects the following parameters:
        name - the slice name, i.e. 'iupui_ndt', or 'mlab_neubot'
      Optional:
        index - int, the index in the 12-slots for slices with IPv4 addresses.
        attrs - [], a list of Attr() objects with attributes for this slice.
        use_initscript - bool, default is False.  If True, use the
                    mlab_generic_initscript for this slice.  The initscript
                    sets up the slice yum repos on first-creation to
                    automatically install a custom rpm package.  In particular, 
                    the rpm package should be named the same as the slicename.
                    For slice iupui_ndt, the initscript installs the custom
                    package called "iupui_ndt-*.rpm" automatically.
                    CAUTION: this attribute is applied per-node.  Also, only to
                    nodes on which plsync is called explicitly.
        ipv6 - how to enable IPv6 for this slice. Options are:
                "all" - add IPv6 addres to all nodes
                [] - a list of abbreviated hostnames, i..e ['mlab1.nuq01', 
                    'mlab2.nuq02', ...]
                None - do not enble IPv6 addressing anywhere.
    """

    def __str__(self):
        return "\n%s \n\t %s" % (self['name'], pprint.pformat(self))

    def __init__(self, **kwargs):
        if 'name' not in kwargs:
            raise Exception(("The first argument should be the name "+
                             "of a NodeGroup, hostname, or None"))
        if 'index' not in kwargs:
            kwargs['index'] = None
        if 'use_initscript' not in kwargs:
            kwargs['use_initscript'] = False
        if 'ipv6' not in kwargs:
            # None means ipv6 is OFF by default
            kwargs['ipv6'] = None
        else:
            if type(kwargs['ipv6']) == str:
                kwargs['ipv6'] = "all"
            elif type(kwargs['ipv6']) == type([]):
                domain = '.measurement-lab.org'
                kwargs['ipv6'] = [ h+domain for h in kwargs['ipv6'] ]
            else:
                raise Exception("Unrecognized type for ipv6 parameter: %s" % 
                                    type(kwargs['ipv6']))

        if 'attrs' not in kwargs:
            kwargs['attrs'] = []
        kwargs['network_list'] = []

        super(Slice, self).__init__(**kwargs)

    def add_node_address(self, node):
        self['network_list'].append((node.hostname(), node))

    def ipv6_is_enabled(self, hostname):
        return ((isinstance(self['ipv6'], list) and hostname in self['ipv6']) or
                (isinstance(self['ipv6'], str) and "all" == self['ipv6']) )
        
    def sync(self, hostname_or_site=None, skipwhitelist=False, 
             skipsliceips=False, createslice=False):
        """ Create and/or verify the object in the myplc DB """
        # NOTE: USERS  ARE NOT ADDED TO SLICES HERE.
        if createslice:
            print "Making slice! %s" % self['name']
            MakeSlice(self['name'])
        SyncSliceExpiration(self['name'])

        for attr in self['attrs']:
            SyncSliceAttribute(self['name'], attr)
        for h,node in self['network_list']:
            if ( hostname_or_site is None or 
                 hostname_or_site == h    or 
                 hostname_or_site in h ):
                if not skipwhitelist:
                    # add this slice to whitelist of all hosts.
                    WhitelistSliceOnNode(self['name'], h)
                    #RemoveSliceFromNode(self['name'], h)
                if not skipsliceips:
                    attr = node.get_interface_attr(self)
                    if attr:
                        SyncSliceAttribute(self['name'], attr)

                # NOTE: use_initscript is set and hostname_or_site is explicit
                if self['use_initscript'] and hostname_or_site is not None:
                    # NOTE: assign the mlab_generic_initscript to slices on 
                    #       this node.
                    # TODO: this needs to be waaay more flexible.
                    attr = Attr(node.hostname(), 
                                initscript="mlab_generic_initscript")
                    SyncSliceAttribute(self['name'], attr)
        return

