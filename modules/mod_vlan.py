#!/bin/python -tt
# -*- coding: utf-8 -*-
# vim: tabstop=12 expandtab shiftwidth=4 softtabstop=4

# author: William Leemans <willie@elaba.net>
# copyright: Copyright 2015, William Leemans
# license: GPL v3

#import sys
#import re
#from jinja2 import Template
import os
import yaml
from netaddr import IPAddress,IPNetwork,IPRange

class mod_vlan():
    _hostvars = dict()
    _hostgroups = dict()
    _config = dict()
    _args = dict()
    _org_hostvars = dict()

    def __init__( self, config=dict(), args=dict(), hostvars=dict() ):
        self._config = config
        self._args = args
        self._org_hostvars = hostvars
  
    def getHostvars(self):
        ipv4_addr = dict()
        if os.path.isfile(self._args["file"]):
            with open(self._args["file"], 'r') as f:
                vlan_info = yaml.load(f)
            for vlan in vlan_info:
                ipv4_net = IPNetwork(vlan_info[vlan]["ipv4_network"]+"/"+vlan_info[vlan]["ipv4_netmask"])
                ipv4_range = IPRange(ipv4_net[1],ipv4_net[-2])
                for el in list(ipv4_range):
                    #ipv4_addr.update( {str(el): vlan_info[vlan]} )
                    ipv4_addr.update( {str(el): vlan} )
        #else:
        #    return self._hostvars

        for hostname in self._org_hostvars:
            self._hostvars[hostname] = dict()
            self._hostvars[hostname][self._args["prefix"] + "vlan"] = -1
            self._hostvars[hostname][self._args["prefix"] + "ipv4_network"] = "unknown"
            self._hostvars[hostname][self._args["prefix"] + "ipv4_netmask"] = "unknown"
            self._hostvars[hostname][self._args["prefix"] + "ipv4_gateway"] = "unknown"
            try:
                self._org_hostvars[hostname][self._args["ipv4_hostvar_fact"]]
            except:
                continue

            host_ipv4_addr = self._org_hostvars[hostname][self._args["ipv4_hostvar_fact"]]

            try:
                ipv4_addr[host_ipv4_addr]
            except:
                continue
            else:
                vlan_id = vlan_info[ipv4_addr[host_ipv4_addr]]["vlan"]
                ipv4_network = vlan_info[ipv4_addr[host_ipv4_addr]]["ipv4_network"]
                ipv4_netmask = vlan_info[ipv4_addr[host_ipv4_addr]]["ipv4_netmask"]
                ipv4_gateway = vlan_info[ipv4_addr[host_ipv4_addr]]["ipv4_gateway"]
                #self._hostvars[hostname][self._args["prefix"] + "vlan"] = ipv4_addr[host_ipv4_addr]["vlan"]
                #self._hostvars[hostname][self._args["prefix"] + "ipv4_network"] = ipv4_addr[host_ipv4_addr]["ipv4_network"]
                #self._hostvars[hostname][self._args["prefix"] + "ipv4_netmask"] = ipv4_addr[host_ipv4_addr]["ipv4_netmask"]
                #self._hostvars[hostname][self._args["prefix"] + "ipv4_gateway"] = ipv4_addr[host_ipv4_addr]["ipv4_gateway"]
                self._hostvars[hostname][self._args["prefix"] + "vlan"] = vlan_id
                self._hostvars[hostname][self._args["prefix"] + "ipv4_network"] = ipv4_network
                self._hostvars[hostname][self._args["prefix"] + "ipv4_netmask"] = ipv4_netmask
                self._hostvars[hostname][self._args["prefix"] + "ipv4_gateway"] = ipv4_gateway

                            
        return self._hostvars

    def getGroups(self):
        return self._hostgroups

    def help(self):
        return """mod_static.py help
module configuration:
There is no specific configuration of this module

hostvars configuration:
[static-hostvars]      name it however you want...
module             mandatory, name of the modules (vlan in this case)
description        optional, describe the datasource
prefix             optional, a prefix for every MariaDB field
file               mandatory, location of the yml vlan file
ipv4_hostvar_fact  mandatory, existing hostvar fact name


groups configuration:
N/A

The vlan yaml must be of the following format:
<vlan_id>:
    vlan: <vlan_id>
    ipv4_network: <ipv4 network>
    ipv4_netmask: <ipv4 netmask. can be cidr or full notation>
    ipv4_gateway: <ipv4 gateway address>

eg.
1000:
    vlan: 1000
    ipv4_network: 192.168.0.0
    ipv4_netmask: 255.255.255.0
    ipv4_gateway: 192.168.0.1
"""
