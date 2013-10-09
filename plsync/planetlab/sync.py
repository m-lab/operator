import session as s
import sys
import pprint
import time
import base64

# NOTE: PLCAPI xmlrpclib.Fault codes are define in:
# http://git.planet-lab.org/?p=plcapi.git;a=blob;f=PLC/Faults.py
PLCAuthenticationFailureCode=103

def handle_xmlrpclib_Fault(funcname, exception):
    """ Checks if exception.faultCode is due to a PLC authentication/role
    failure and exits if so.  Otherwise, the last exception is re-raised.

    Args:
        funcname - string, name of function that produced this fault
        exception - Exception, produced by xmlrpclib.Fault
    Returns:
        Never returns, either raises exception or exits.
    Raises:
        Exception
    Exits:
        if exception.faultCode is due to a PLC Authentication Failure.
    """
    if (type(exception) == xmlrpclib.Fault and
         exception.faultCode == PLCAuthenticationFailureCode):
        print "Error: %s requires a different role." % funcname
        print "Error: Consider contacting support@planet-lab.org for assistance"
        print exception
        sys.exit(1)
    # NOTE: if we have not exited, re-raise the last exception
    raise

def SyncSiteTag(sitename, site_id, tagname, value):
    """ SyncSiteTag() - either add, confirm, or update the tagname->value

    Args:
        sitename - string, name of site, used for messages only
        site_id - int, site id returned from GetSites()
        tagname - string, name of tag to set
        value - string, tag value, even numbers should be passed as strings.
    Returns:
        site_tag_id on Add*
        status code on Update* (1 or not-1 for success or failure)
        None - on Confirm
    """
    tags = s.api.GetSiteTags({'site_id' : site_id, 'tagname' : tagname})
    if len(tags) == 0:
        print "ADDING: site tag to %s tag(%s->%s)" % (sitename, tagname, value)
        return s.api.AddSiteTag(site_id, tagname, value)
    elif len(tags) == 1:
        tag = tags[0]
        if tag['value'] == value:
            print ("Confirmed: site tag on %s tag(%s->%s)" % 
                   (sitename, tagname, value))
        else:
            print ("UPDATE: site tag on %s from tag(%s->%s) to %s" % 
                   (sitename, tagname, tag['value'], value))
            return s.api.UpdateSiteTag(tag['site_tag_id'], tagname, value)
    else:
        print "Error: SyncSiteTag()"
        print "Error: This should never happen, but here we are."
        print "Error: Received multiple tags for tagname(%s)" % tagname
        print "Error: %s" % tags
        sys.exit(1)

def SyncLocation(sitename, location):
    """ SyncLocation - assigns location information to a Site.

        Args:
            sitename - string, name of site, i.e. 'mlabnuq0t'
            location - Location() object or None
        Returns:
            Nothing

        If myplc does not have these tags set automatically, you can create
        them using 'plcsh' and running these commands:
            AddTagType({'tagname' : 'city', 
                        'description' : 'The city where this site is located', 
                        'category' : 'site/location'})
            AddTagType({'tagname' : 'country', 
                        'description' : 'The country where this site is located', 
                        'category' : 'site/location'})
            AddTagType({'tagname' : 'extra', 
                        'description' : 'Extra context information for a site', 
                        'category' : 'site/extra'})
        The commands in this function depend on them existing.
    """
    if location is None:
        # NOTE: nothing to do.
        return

    # NOTE: AddSiteTag() only recognizes the numeric site_id, :-/
    sites = s.api.GetSites(sitename, ['site_id', 'latitude', 'longitude'])
    if len(sites) != 1: 
        msg = "Error: GetSites(%s) returned: %s sites, expected 1"
        print msg % (sitename, len(sites))
        sys.exit(1)

    site_id = sites[0]['site_id']
    SyncSiteTag(sitename, site_id, 'city', location['city'])
    SyncSiteTag(sitename, site_id, 'country', location['country'])

    # NOTE: always update latitude/longitude, 
    update = {}
    if location['latitude'] != sites[0]['latitude']:
        update['latitude'] = location['latitude']
    if location['longitude'] != sites[0]['longitude']:
        update['longitude'] = location['longitude']

    if len(update) != 0:
        print ("UPDATE: site lat/long from %s,%s to %s" % 
                (location['latitude'], location['longitude'], update))
        s.api.UpdateSite(site_id, update)

    if 'extra' in location:
        SyncSiteTag(sitename, site_id, 'extra', location['extra'])

def MakeSite(loginbase,name,abbreviated_name, 
                       url="http://www.measurementlab.net/"):
    """
        MakeSite() - adds or confirms the existence of given site.
                     updates are not performed.

        Args:
            loginbase - name of site i.e mlabnuq01
            name - long presentation name of site. i.e. Measurement Lab NUQ01
            abbreviated_name - short presentation name of site, i.e. M-Lab NUQ01
            url - website associated with site.  Used to identify mlab by data
                    collection pipeline.
        Returns:
            site_id
    """
    site = s.api.GetSites({"login_base":loginbase})
    if len(site) == 0:
        print "MakeSite(%s,%s,%s)"%(loginbase,name,abbreviated_name)
        # NOTE: max_slices defaults to zero
        try:
            site_id = s.api.AddSite({"name":name,
                     "abbreviated_name":abbreviated_name,
                     "login_base": loginbase,
                     "url" : url, 'max_slices' : 10})
        except xmlrpclib.Fault, e:
            handle_xmlrpclib_Fault("AddSite()", e)

    elif len(site) == 1:
        print "Confirmed: %s is in DB" % loginbase
        site_id = site[0]['site_id']
    else:
        print "Error: PLCAPI returned two sites for a single name."
        print "Error: This should never happen, but here we are."
        print "Error: Double-check sitename(%s) and db" % loginbase
        sys.exit(1)

    return site_id

def MakePerson(first_name, last_name, email):
    persons = s.api.GetPersons({"email":email,"enabled":True},
                               ["site_ids","email","person_id"])
    if len(persons)==0:
        print "Adding person %s" % email
        fields = {"first_name":first_name, "last_name":last_name, 
                  "email":email, "password":"clara_abcdefg"}
        try:
            s.api.AddPerson(fields)
        except xmlrpclib.Fault, e:
            handle_xmlrpclib_Fault("AddPerson()", e)
        s.api.UpdatePerson(personid, {'enabled': True})
    return

def GetPersonsOnSite(loginbase):
    site_list = s.api.GetSites({"login_base":loginbase})
    if len(site_list) == 0:
        raise Exception("WARNING: no site found for %s" % loginbase)
    if len(site_list) > 1:
        raise Exception("WARNING: multiple sites found for %s" % loginbase)

    site = site_list[0]
    person_list = s.api.GetPersons(site['person_ids'])
    return person_list

def DeletePersonFromSite(email, loginbase):
    print "Deleting %s from site %s" % (email, loginbase)
    try:
        s.api.DeletePersonFromSite(email, loginbase)
    except xmlrpclib.Fault, e:
        handle_xmlrpclib_Fault("DeletePersonFromSite()", e)

def AddPersonToSite(email,loginbase):
    print "Adding %s to site %s" % (email, loginbase)
    try:
        s.api.AddPersonToSite(email,loginbase)
    except xmlrpclib.Fault, e:
        handle_xmlrpclib_Fault("AddPersonToSite()", e)

def SyncPersonsOnSite(user_list, loginbase, createusers=False):
    """ A user in user_list is in one of three categories:
    1) declared in user_list and a member of site - confirmed users
    2) declared in user_list but not a member of site - users to add
    3) not declared in user_list and a member of site - users to delete

    This function adds declared users not yet a member of the site and deletes
    undeclared users that are a member of the site.
    """
    members_of_site = GetPersonsOnSite(loginbase)
    member_emails = [ p['email'] for p in members_of_site ]
    delcared_emails = [ email for fn,ln,email in user_list ]

    def is_a_current_member(x):
        return x[2] in member_emails
    def is_not_a_current_member(x):
        return x[2] not in member_emails
    def is_not_a_declared_user(x):
        return x not in delcared_emails

    persons_confirmed = filter(is_a_current_member, user_list)
    persons_to_add = filter(is_not_a_current_member, user_list)
    emails_to_delete = filter(is_not_a_declared_user, member_emails)

    for person in persons_confirmed:
        print "Confirmed %s is member of site %s" % (person[2], loginbase)

    for person in persons_to_add:
        if createusers: MakePerson(*person)
        email = person[2]
        AddPersonToSite(email,loginbase)

    for email in emails_to_delete:
        DeletePersonFromSite(email,loginbase)

    return

def MakeNode(login_base, hostname):
    node_list = s.api.GetNodes(hostname)
    if len(node_list) == 0:
        print "Adding Node %s to site %s" % (hostname, login_base)
        node_id = s.api.AddNode(login_base, { 'boot_state' : 'reinstall',
                                            'model' : 'unknown',
                                            'hostname' : hostname,} )
    else:
        node_id = node_list[0]['node_id']       

    return node_id
 
def MakePCU(login_base, node_id, pcu_fields):
    pcu_list = s.api.GetPCUs({'hostname' : pcu_fields['hostname']})
    if len(pcu_list) == 0:
        print "Adding PCU to %s: %s", (node_id, pcu_fields )
        pcu_id = s.api.AddPCU(login_base, pcu_fields)
        s.api.AddNodeToPCU(node_id, pcu_id, 1)
    else:
        if node_id in pcu_list[0]['node_ids']:
            print ("Confirmed PCU %s is associated with node %d" % 
                    (pcu_list[0]['hostname'], node_id))
            pcu_id = pcu_list[0]['pcu_id']
        else:
            print "ERROR: need to add pcu node_id %s" % node_id
            sys.exit(1)
    return pcu_id

def SyncNodeTag(hostname, node_id, tagname, value):
    """
       SyncNodeTag() - Adds, Updates, or Confirms the assignment of the given
                       tagname and value on the given hostname/node_id.
       Args:
        hostname - string, used for printing
        node_id - int, node_id of hostname within plcdb, from previous call to
                    GetNodes().
        tagname - string, the name of a pre-existing NodeTagType.
        value - string, the value of this tag.

       Returns:
        None

       Exits on errors.
    """
    # NOTE: accept that node_id is valid.
    # NOTE: lookup all NodeTags with tagname:value
    tags = s.api.GetNodeTags({'node_id': node_id, 
                              'tagname' : tagname})
    # NOTE: only one distinct tagname allowed per node.
    if len(tags) > 1:
        print ("ERROR: found %s tags for %s on %s" % 
               (len(tags), tagname, hostname))
        print ("ERROR: expected only 1, plese correct this.")
        sys.exit(1)

    if len(tags) == 0:
        # NOTE: not present, add it!
        print "ADDING: nodetag %s->%s on %s" % (tagname, value, hostname)
        s.api.AddNodeTag(node_id, tagname, value)
    else:
        tag = tags[0]
        if tag['value'] != value:
            print ("UPDATE: nodetag from %s->%s on %s" % 
                   (tag['value'], value, hostname))
            s.api.UpdateNodeTag(tag['node_tag_id'], value)
        else:
            print ("Confirmed: nodetag %s->%s is set on %s" %
                   (tagname, value, hostname))

def PutNodeInNodegroup(hostname, node_id, nodegroup_name):
    """
       PutNodeInNodegroup() -- A specialty function for setting up a node's
            NodeGroup and nodetags.  It is less generic than other Sync*
            functions because it operates on the 'deployment' nodetag and
            'fcdistro' nodetags.  See 'SyncNodeTag()' for general nodetag
            syncing.

       Args:
        hostname - string, used for printing
        node_id - int, node_id of hostname within plcdb, from previous call to
                    GetNodes().
        nodegroup_name - string, name of new nodegroup. (one per node).

       Returns:
        None

       Exits on errors.
    """
    node_list = s.api.GetNodes(node_id, ['nodegroup_ids', 'node_tag_ids'])
    nodegroup_list = s.api.GetNodeGroups({'groupname' : nodegroup_name}, 
                                         ['nodegroup_id'])
    if len(nodegroup_list) != 1:
        print ("ERROR: found %s nodegroups when looking for %s in plc db" % 
                (len(nodegroup_list), nodegroup_name)) 
        print "ERROR: expected 1; please double check configuration"
        sys.exit(1)

    if len(node_list) != 1:
        print ("ERROR: found %s hosts when looking for %s in plc db" % 
                (len(node_list), hostname))
        print "ERROR: expected 1; please double check configuration"
        sys.exit(1)

    # NOTE: both node and nodegroup are in the plc DB.
    ng_id = nodegroup_list[0]['nodegroup_id'] 
    node_ng_ids = node_list[0]['nodegroup_ids']
    if ng_id not in node_ng_ids:
        SyncNodeTag(hostname, node_id, 'deployment', nodegroup_name)
    else:
        print ("Confirmed: %s is in nodegroup %s" %
               (hostname, nodegroup_name))

    # TODO: find a better place for this.
    if nodegroup_name in ['MeasurementLabCentos']:
        SyncNodeTag(hostname, node_id, 'fcdistro', 'centos6')

def setTagTypeId(tagname, tags):
    tagtype_list = s.api.GetTagTypes({"tagname":tagname})
    if len(tagtype_list)==0:
        print "BUG: %s TagType does not exist. Need to update MyPLC" % tagname
        sys.exit(1)
    else:
        assert(len(tagtype_list)==1)
        tags['tag_type_id'] = tagtype_list[0]['tag_type_id']
    return tags

def SyncInterfaceTags(node_id, interface, tagvalues):
    """
        SyncInterfaceTags -- 
            arguments: node_id, interface on node, new interface tags 

            SyncInterfaceTags will find interface on the given node.

            Then it will compare the provided tagvalues to the existing tags on
            the interface.  When the provided tags are missing, they are added.
            When the provided tags are present, the value is verified, or
            updated when the provided value is different from the stored value.

            Additional logic is necessary to lookup tag-types prior to adding
            the tags to the interface.

            Extra tags already present on interface are ignored.
    """
    filter_dict = { "node_id" : node_id, 'ip' : interface['ip'] }
    interface_found = s.api.GetInterfaces(filter_dict)
    interface_tag_ids_found = interface_found[0]['interface_tag_ids']
    current_tags = s.api.GetInterfaceTags(interface_tag_ids_found)

    new_tags = {}
    for tagname in tagvalues.keys():
        new_tags[tagname] = { "tag_type_id":None, 
                              "current_tag":None, 
                              "value": tagvalues[tagname] }

        for current_tag in current_tags:
            name = current_tag['tagname']
            if new_tags.has_key(name):
                new_tags[name]['current_tag']=current_tag

        # set tag type so we can pass the tagtypeid to AddTag later.
        setTagTypeId(tagname, new_tags[tagname])

    for tagname,tag in new_tags.iteritems():
        if tag['current_tag'] is None:
            print ("ADD: tag %s->%s for %s" %
                    (tagname,tag['value'],interface['ip']))
            interface_id = interface_found[0]['interface_id']
            type_id = tag['tag_type_id']
            tag_id = s.api.AddInterfaceTag(interface_id,type_id,tag['value'])
            if tag_id <= 0:
                print "BUG: AddInterfaceTag(%d,%s) failed" % (
                            interface_found[0]['interface_id'],tag['value'])
                sys.exit(1)
        else:
            # current_tag is present on Interface already
            # check to see if it's 
            current_tag = tag['current_tag']
            if (tag['value'] != current_tag['value'] and 
                tagname not in [ 'alias' ]):
                print ("UPDATE: tag %s from %s->%s for %s" %
                        (tagname,current_tag['value'],tag['value'],
                         interface['ip']))
                tag_id = current_tag['interface_tag_id']
                s.api.UpdateInterfaceTag(tag_id,tag['value'])
            else:
                print ("Confirmed: tag %s = %s for %s" %
                        (tagname, tag['value'], interface['ip']))

def InterfacesAreDifferent(declared, found):
    """ return True if the two dicts are different """
    if len(declared.keys()) == 0:
        return True
    for key in declared.keys():
        if key not in found:
            print "key not found in interface dict: %s" % key
            return True
        if declared[key] != found[key]:
            print ("values not equal in interface dict: declared[%s] "+
                   "== found[%s] :: %s == %s") % (key, key, declared[key], 
                                                    found[key])
            return True
    return False

def SyncInterface(hostname, node_id, interface, is_primary):
    """
    SyncInterface() -- Adds, updates, or confirms node interface.

    Args:
        hostname - fqdn of node
        node_id - node_id from plcdb
        interface - a dict() defining all fields for a plcdb interface object.
        is_primary - a boolean indicating whether this interface is the primary
        interface for the node (assigned to root context) or a supplemental one
        (assigned to slices).

    Returns:
        None
    """
    primary_declared = interface
    filter_dict = {"node_id" : node_id, 
                   "is_primary" : is_primary, 
                   "ip" : interface['ip']}
    interface_found = s.api.GetInterfaces(filter_dict)

    if len(interface_found) == 0:
        print ("Adding: node network %s to %s" %
                (primary_declared['ip'], hostname))
        i_id = s.api.AddInterface(node_id, primary_declared)
    else:
        # TODO: clear any interface settings from primary interface
        if InterfacesAreDifferent(primary_declared, interface_found[0]):
            if len(primary_declared.keys()) == 0:
                print ("WARNING: found primary interface for %s in "+
                        "DB, but is NOT SPECIFIED in config!") % hostname
                pprint.pprint(interface_found[0])
            else:
                pprint.pprint( primary_declared )
                pprint.pprint( interface_found[0] )
                print "Updating: node network for %s to %s" % (
                            hostname, primary_declared)
                s.api.UpdateInterface(interface_found[0]['interface_id'], 
                                      primary_declared)
        else:
            print ("Confirmed: node network setup for %s for %s" %
                    (hostname, interface['ip']))
        i_id = interface_found[0]['interface_id']

    # NOTE: everything that follows is only for non-primary interfaces.
    if is_primary is not True:
        goal = {
            "alias"  : str(i_id),
            "ifname" : "eth0"
        }
        SyncInterfaceTags(node_id, interface, goal)

def MakeSlice(slicename):
    """ MakeSlice() creates the given slicename or confirms that it exists.

        Args:
            slicename - string, the name of the slice to create i.e. 'iupui_ndt'
        Returns:
            slice_id of slicename, int
    """
    sl = s.api.GetSlices({'name' : slicename})
    if len(sl) == 0:
        try:
            slice_id = s.api.AddSlice({'name' : slicename,
                    'url' : 'http://www.measurementlab.net', 
                    'description' : 'Fake description for testing'})
        except xmlrpclib.Fault, e:
            handle_xmlrpclib_Fault("AddSlice()", e)

        print "Adding:    Slice %s:%s" % (slicename, slice_id)
    elif len(sl) == 1:
        slice_id = sl[0]['slice_id']
        print "Confirmed: Slice %s:%s" % (slicename, slice_id)
    else:
        print "Error: PLCAPI returned two slices for a single name."
        print "Error: This should never happen, but here we are."
        print "Error: Double-check slicename(%s) and db" % slicename
        sys.exit(1)

    return slice_id

def AddSliceTag(slicename, key, value, node, nodegroup):
    """ AddSliceTag() calls s.api.AddSliceTag() with the correct set of arguments.
        Args:
            slicename - string slicename i.e. "iupui_ndt"
            key - the slice tag name, i.e. "vsys"
            value - the value for the slice tag, i.e. "web100_proc_write"
            node - a single node to assign this tag to, or None.  Single-node
                    slice tags are used for the 'ip_addresses' slice tag.
            nodegroup - a single node group to assign this tag to, or None.
                    Single-group slice tags are used for attributes that are
                    applicable only in one nodegroup but not others. An example
                    is M-Lab's nodegroup within Planetlab.
        Returns:
            result of s.api.AddSliceTag()
    """
    print ("ADDING   : %s -> (%s->%s,%s,%s)" %
           (slicename, key, value, node, nodegroup))
    if node is None and nodegroup is None: 
        return s.api.AddSliceTag(slicename, key, value)
    elif nodegroup is None:
        return s.api.AddSliceTag(slicename, key, value, node)
    else:
        return s.api.AddSliceTag(slicename, key, value, node, nodegroup)

    # catch-all unreachable.
    return None

def SyncSliceAttribute(slicename, attr):
    """ SyncSliceAttribute() assigns the given attributes to the slice.
        If attributes were not previously added, they are added.
        If attributes were previously added, their value is verified.
        If attributes were previously added and changed, their value is updated.

        Only one tag name 'vsys' can have multiple values.
    Args:
        slicename - string, name of slice to apply attributes.
        attr - An Attr() object.
    Returns:
        None
    Raises:
        Exception() if Attr() object is misformed.
        exit()s if multiple slice tags are present for a single-tag attribute.
    """

    tag_filter = {'name' : slicename}
    #print slicename, attr
    nd_id=None
    ng_id=None
    if attr['attrtype'] == "all":
        # apply to all nodes
        ng=None
        nd=None
    elif attr['attrtype'] == "hostname":
        # apply to a node
        ng=None
        nd=attr[attr['attrtype']]
        nd_id = s.api.GetNodes({'hostname' : nd}, ['node_id'])[0]['node_id']
        tag_filter['node_id'] = nd_id
    elif attr['attrtype'] == "nodegroup":
        # apply to a nodegroup
        ng=attr[attr['attrtype']]
        ng_id = s.api.GetNodeGroups({'groupname' : ng}, 
                        ['nodegroup_id'])[0]['nodegroup_id']
        # NOTE: ']' means >=, '[' means <= 
        # HACK: these two directives work around a bug that prevents search 
        #       on strict match.  Need to submit patch.
        tag_filter[']nodegroup_id'] = ng_id
        tag_filter['[nodegroup_id'] = ng_id
        nd=None
    else:
        raise Exception("no attrtype in %s" % attr)

    sub_attr = {}
    for k in attr.keys():
        if k not in ['attrtype', attr['attrtype']]:
            sub_attr[k] = attr[k]
            # NOTE: GetSliceTags does not support nodegroup_id filtering :-/
            tag_filter['tagname'] = k
            sliceattrs = s.api.GetSliceTags(tag_filter)
            attrsfound = filter(lambda a: a['value'] == attr[k], sliceattrs)
            if k in ['vsys']:
                # NOTE: these keys can have multiples with different values.
                #       So, do not perform updates.
                if len(attrsfound) == 0:
                    AddSliceTag(slicename, k, attr[k], nd, ng)
                elif len(attrsfound) >= 1:
                    confirmed = False
                    for af in attrsfound:
                        if ( af['node_id'] == nd_id and 
                             af['nodegroup_id'] == ng_id ):
                            if af['value'] == attr[k]:
                                print ("Confirmed: %s -> (%s,%s,%s,%s)" %
                                        (slicename, k, attr[k], nd, ng))
                                confirmed=True
                    if not confirmed:
                        print "Found attr value but maybe in wrong NG/Node?"
                        print "?SHOULD I UPDATE THIS? %s with %s" % (af, attr)
                        #s.api.AddSliceTag(slicename, k, attr[k], nd, ng)
            else:
                # NOTE: these keys should only have a single value for the 
                #       given key, so do perform updates.
                if len(sliceattrs) == 0:
                    AddSliceTag(slicename, k, attr[k], nd, ng)

                elif len(sliceattrs) == 1:
                    if ( sliceattrs[0]['node_id'] == nd_id and 
                         sliceattrs[0]['nodegroup_id'] == ng_id ):
                        if sliceattrs[0]['value'] == attr[k]:
                            print ("Confirmed: %s -> (%s,%s,%s,%s)" %
                                    (slicename, k, attr[k], nd, ng))
                        else:
                            print ("UPDATING : %s -> (%s,%s,%s)" % 
                                    (slicename, k, nd, ng)) 
                            print ("         : from '%s' to '%s'" %
                                    (sliceattrs[0]['value'], attr[k]))
                            s.api.UpdateSliceTag(sliceattrs[0]['slice_tag_id'],
                                                 attr[k])
                    else:
                        print ("Uh-oh: slice tag %s->%s on %s" %
                                (k, attr[k], slicename))
                        print ("        missing ng_id:%s or nd_id:%s" %
                                (ng_id, nd_id))
                        #print "DELETING : multiple SliceTags that match : %s" % tag_filter
                        #for x in sliceattrs:
                        #    print "DELETING : %s" % x
                        #    s.api.DeleteSliceTag(x['slice_tag_id'])
                        #AddSliceTag(slicename, k, attr[k], nd, ng)
                else:
                    # NOTE: this gets more complicated.
                    print "ERROR: multiple SliceTags match: %s" % tag_filter
                    #print "DELETING : multiple SliceTags that match : %s" % tag_filter
                    #for x in sliceattrs:
                    #    print "DELETING : %s" % x
                    #    s.api.DeleteSliceTag(x['slice_tag_id'])
                    #AddSliceTag(slicename, k, attr[k], nd, ng)
                    for x in sliceattrs:
                        print x
                    sys.exit(1)

    #assigned = filter(lambda attr: attr['node_id'] == node['node_id'], 
    #                  sliceattrs)
    #if len(assigned) != 0:
    #    print ("Deleting: slice tag ip_addresses from %s on %s" %
    #            (slicename, node['hostname']))
    #    api.DeleteSliceTag(assigned[0]['slice_tag_id'])
    #api.AddSliceTag(slicename, 'ip_addresses', nnet['ip'], node['node_id'])

EXPIRE_DELTA_90DAYS = (90*60*60*24)
EXPIRE_DELTA_20YEARS = (20*365*60*60*24)

def SyncSliceExpiration(slicename):
    slices = s.api.GetSlices(slicename)
    if len(slices) != 1:
        print "ERROR: GetSlices returned %s results" % len(slices)
        print "       GetSlices('%s') should only return 1 result" % slicename
        sys.exit(1)
    sslice = slices[0]
    current_time = int(time.time())
    if sslice['expires'] < current_time + EXPIRE_DELTA_90DAYS:
        print "Updating slice %s expiration to 20 years from now" % slicename
        attr = {'expires' : current_time + EXPIRE_DELTA_20YEARS}
        s.api.UpdateSlice(slicename, attr)

def RemoveSliceFromNode(slicename, hostname):
    """ RemoveSliceFromNode()

        When retiring a slice from M-lab, the slice needs to be removed from
        M-Lab nodes and it's node-specific slice attributes need to be deleted.
        The slice itself will remain in the DB, while we use PlanetLab.  Once
        M-Lab has it's own aggregate, legacy slice management can be
        re-evaluated.

        This function removes the slice from node and node whitelist.

    Args:
        slicename - name of slice to remove
        hostname - name of machine to remove 
    Returns:
        None

    """
    nodes = s.api.GetNodes(hostname)
    slices = s.api.GetSlices(slicename)

    for node in nodes:
        slice_ids_on_node = node["slice_ids"]
        slice_ids_on_node_whitelist = node["slice_ids_whitelist"]

        for sslice in slices:

            if sslice['slice_id'] in slice_ids_on_node_whitelist:
                # then this slice is not on this node's whitelist
                print ("Removing %s from whitelist on host: %s" %
                        (sslice['name'], node['hostname']))
                s.api.DeleteSliceFromNodesWhitelist(sslice['slice_id'],
                                               [node['hostname']])
            else:
                print ("Confirmed: %s is removed from whitelist on %s" %
                        (sslice['name'], node['hostname']))

            if sslice['slice_id'] in slice_ids_on_node:
                print ("Removing %s from host: %s" %
                        (sslice['name'], node['hostname']))
                s.api.DeleteSliceFromNodes(sslice['slice_id'],
                                           [node['hostname']])
            else:
                print ("Confirmed: %s is removed from %s" %
                        (sslice['name'], node['hostname']))
    return

def WhitelistSliceOnNode(slicename, hostname):
    """
        confirm that slice is added to each host both with
            AddSliceToNodesWhitelist
            AddSliceToNodes
        any slice not in this list.
        
        NOTE: however, stray slices are not deleted from hosts 
    """

    # Add slices to Nodes and NodesWhitelist
    nodes = s.api.GetNodes(hostname)
    slices = s.api.GetSlices(slicename)

    for node in nodes:
        slice_ids_on_node = node["slice_ids"]
        slice_ids_on_node_whitelist = node["slice_ids_whitelist"]

        for sslice in slices:

            if sslice['slice_id'] not in slice_ids_on_node_whitelist:
                # then this slice is not on this node's whitelist
                print ("Adding %s to whitelist on host: %s" %
                        (sslice['name'], node['hostname']))
                try:
                    s.api.AddSliceToNodesWhitelist(sslice['slice_id'],
                                               [node['hostname']])
                except xmlrpclib.Fault, e:
                    handle_xmlrpclib_Fault("AddSliceToNodesWhitelist()", e)
            else:
                print ("Confirmed: %s is whitelisted on %s" %
                        (sslice['name'], node['hostname']))

            if sslice['slice_id'] not in slice_ids_on_node:
                print ("Adding %s to hosts: %s" %
                        (sslice['name'], node['hostname']))
                s.api.AddSliceToNodes(sslice['slice_id'],[node['hostname']])
            else:
                print ("Confirmed: %s is assigned to %s" %
                        (sslice['name'], node['hostname']))
            
    # NOTE: this approach does not delete stray slices from whitelist
    return

def GetBootimage(hostname, imagetype="iso"):
    """ get_bootimage() - generate a new boot image for the named node, and
    media type.  Generating a new ISO, replaces the old node key in the myplc
    db.  So, this is a destructive operation.

    Args:
        hostname - full hostname of system already registered in myPLC db.
        type - type of boot image to fetch.  You should only use 'iso' on M-Lab.
               'usb' is supported by the API call, but most usb sticks do not
               include a read-only switch, so for security reasons are not
               recommended.

    Returns:
        None
    """
    if imagetype not in ['iso', 'usb']:
        print "ERROR: GetBootimage() called with imagetype=%s" % imagetype
        print "ERROR: imagetype should be either: iso, or usb"
        sys.exit(1)

    # NOTE: returns a gigantic blob of base64 encoded text.
    x = s.api.GetBootMedium(hostname, 'node-%s' % imagetype, "", [])
    bindata = base64.b64decode(x)
    
    # NOTE: save file to pwd
    fname = "%s.%s" % (hostname, imagetype)
    f = open(fname, 'w')
    f.write(bindata)
    f.close()
