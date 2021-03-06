#!/usr/bin/env python
#
# Copyright 2009-2020 NTESS. Under the terms
# of Contract DE-NA0003525 with NTESS, the U.S.
# Government retains certain rights in this software.
#
# Copyright (c) 2009-2020, NTESS
# All rights reserved.
#
# Portions are copyright of other developers:
# See the file CONTRIBUTORS.TXT in the top level directory
# the distribution for more information.
#
# This file is part of the SST software package. For license
# information, see the LICENSE file in the top level directory of the
# distribution.

import sst
from sst.merlin.base import *


class Topology(TemplateBase):
    def __init__(self):
        TemplateBase.__init__(self)
        self._declareClassVariables(["endPointLinks","built","_router_template"])
        self.endPointLinks = []
        self.built = False
    def getTopologyName(self):
        return "NoName"
    #def addParams(self,p):
    #    self._params.update(p)
    #def addParam(self, key, value):
    #    self._params[key] = value
    def build(self, network_name, endpoint = None):
        pass
    def getEndPointLinks(self):
        pass
    def setRouterTemplate(self,template):
        self._router_template = template
    def getNumNodes(self):
        pass


class topoDragonFly(Topology):

    def __init__(self):
        Topology.__init__(self)
        self._declareClassVariables(["link_latency","host_link_latency","global_link_map"])
        self._defineRequiredParams(["hosts_per_router","routers_per_group","intergroup_links","num_groups"])
        self._defineOptionalParams(["algorithm","adaptive_threshold","global_routes"])
        self.global_routes = "absolute"

    def getTopologyName(self):
        return "Dragonfly"


    def getNumNodes(self):
        return self.num_groups * self.routers_per_group * self.hosts_per_router

    def setShape(self,hosts_per_router, router_per_group, intergroup_links, num_groups):
        self.hosts_per_router = hosts_per_router
        self.routers_per_group = routers_per_group
        self.intergroup_links = intergroup_links
        self.num_groups = num_groups


    def setRoutingModeAbsolute(self):
        self.global_routes = "absolute"


    def setRoutingModeRelative(self):
        self.global_routes = "relative"


    def build(self, network_name, endpoint):
        if self.host_link_latency is None:
            self.host_link_latency = self.link_latency

        #self.params.verifyParamsExist(self.topoKeys)
        #endpoint.verifyParams()

        #extraParams = dict()
        #extraParams["topology"] = "merlin.dragonfly"
        num_peers = self.hosts_per_router * self.routers_per_group * self.num_groups

        #self.params["dragonfly:global_route_mode"] = self.global_routes


        total_intergroup_links = (self.num_groups - 1) * self.intergroup_links
        intergroup_per_router = (total_intergroup_links + self.routers_per_group - 1 ) // self.routers_per_group
        #extraParams["intergroup_per_router"] = inter_group_per_router

        empty_ports = intergroup_per_router * self.routers_per_group - total_intergroup_links

        #self.params["router_radix"] = self.routers_per_group - 1 + self.hosts_per_router + self.params["dragonfly:intergroup_per_router"]
        num_ports = self.routers_per_group - 1 + self.hosts_per_router + intergroup_per_router

        #if self.num_groups > 2:
        #    #foo = self.params["dragonfly:algorithm"]
        #    self.topoKeys.append("dragonfly:algorithm")

        links = dict()

        #####################
        def getLink(name):
            if name not in links:
                links[name] = sst.Link(name)
            return links[name]
        #####################

        rpg = self.routers_per_group
        ng = self.num_groups - 1 # don't count my group
        igpr = intergroup_per_router

        if self.global_link_map is None:
            # Need to define global link map

            self.global_link_map = [-1 for i in range(igpr * rpg)]

            # Links will be mapped in linear order, but we will
            # potentially skip one port per router, depending on the
            # parameters.  The variable self.empty_ports tells us how
            # many routers will have one global port empty.
            count = 0
            start_skip = rpg - empty_ports
            for i in range(0,rpg):
                # Determine if we skip last port for this router
                end = igpr
                if i >= start_skip:
                    end = end - 1
                for j in range(0,end):
                    self.global_link_map[i*igpr+j] = count;
                    count = count + 1

        # End set global link map with default


        # g is group number
        # r is router number with group
        # p is port number relative to start of global ports

        def getGlobalLink(g, r, p):
            # Look into global link map to get the dest group and link
            # number to that group
            raw_dest = self.global_link_map[r * igpr + p];
            if raw_dest == -1:
                return None

            # Turn raw_dest into dest_grp and link_num
            link_num = raw_dest // ng;
            dest_grp = raw_dest - link_num * ng

            if ( self.global_routes == "absolute" ):
                # Compute dest group ignoring my own group id, for a
                # dest_grp >= g, we need to add 1 to get the right group
                if dest_grp >= g:
                    dest_grp = dest_grp + 1
            elif ( self.global_routes == "relative"):
                # For relative, add current group to dest_grp + 1 and
                # do modulo of num_groups to get actual group
                dest_grp = (dest_grp + g + 1) % (ng+1)
            #else:
                # should never happen

            src = min(dest_grp, g)
            dest = max(dest_grp, g)

            #getLink("link:g%dg%dr%d"%(g, src, dst)), "port%d"%port, self.params["link_lat"])
            return getLink("%s:global_link:g%dg%dr%d"%(network_name,src,dest,link_num))

        #########################


        router_num = 0
        nic_num = 0
        # GROUPS
        for g in range(self.num_groups):

            # GROUP ROUTERS
            for r in range(self.routers_per_group):
                rtr = self._router_template.instanceRouter("%s:rtr:G%dR%d"%(network_name, g, r))
                #rtr = sst.Component("%s:rtr:G%dR%d"%(network_name, g, r), "merlin.hr_router")
                #rtr.addParams(self.params.subset(self.topoKeys, self.topoOptKeys))
                rtr.addParam("num_ports",num_ports)
                rtr.addParam("id", router_num)

                # Insert the topology object
                sub = rtr.setSubComponent(self._router_template.getTopologySlotName(),"merlin.dragonfly",0)
                sub.addParams(self._params)
                sub.addParam("intergroup_per_router",intergroup_per_router)
                if router_num == 0:
                    # Need to send in the global_port_map
                    #map_str = str(self.global_link_map).strip('[]')
                    #rtr.addParam("dragonfly:global_link_map",map_str)
                    sub.addParam("global_link_map",self.global_link_map)

                port = 0
                for p in range(self.hosts_per_router):
                    #(nic, port_name) = endpoint.build(nic_num, {"num_peers":num_peers})
                    (nic, port_name) = endpoint.build(nic_num, {})
                    if nic:
                        link = sst.Link("link:g%dr%dh%d"%(g, r, p))
                        #network_interface.build(nic,slot,0,link,self.host_link_latency)
                        link.connect( (nic, port_name, self.host_link_latency), (rtr, "port%d"%port, self.host_link_latency) )
                        #rtr.addLink(link,"port%d"%port,self.host_link_latency)
                    nic_num = nic_num + 1
                    port = port + 1

                for p in range(self.routers_per_group):
                    if p != r:
                        src = min(p,r)
                        dst = max(p,r)
                        rtr.addLink(getLink("link:g%dr%dr%d"%(g, src, dst)), "port%d"%port, self.link_latency)
                        port = port + 1

                for p in range(igpr):
                    link = getGlobalLink(g,r,p)
                    if link is not None:
                        rtr.addLink(link,"port%d"%port, self.link_latency)
                    port = port +1

                router_num = router_num +1
