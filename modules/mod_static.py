#!/bin/python -tt
# -*- coding: utf-8 -*-
# vim: tabstop=12 expandtab shiftwidth=4 softtabstop=4

# author: William Leemans <willie@elaba.net>
# copyright: Copyright 2015, William Leemans
# license: GPL v3

import sys
import re
from jinja2 import Template

class mod_static():
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
        try:
            self._args["prefix"]
        except:
            self._args["prefix"] = ""
	
        keyvalpair = dict()
        for el in self._args:
            if re.match('^key[0-9]+$', el) is not None:
                try:
                    self._args["value" + el[3:]]
                except:
                    self._args["value" + el[3:]] = ""
                
                if self._args["value" + el[3:]] != "":
                    keyvalpair.update({self._args[el]:self._args["value" + el[3:]]})

        for hostname in self._org_hostvars:
            hlist = [ el.strip(" ") for el in self._args["applyto"].split(",") ]
            if self._args["applyto"].lower() == "all" or re.match(self._args["applyto"], hostname) is not None or hostname in hlist:
                try:
                    self._hostvars[hostname]
                except:
                    self._hostvars[hostname] = dict()

                for el in keyvalpair:
                    kt = Template(el)
                    vt = Template(keyvalpair[el])

                    k = kt.render(self._org_hostvars[hostname])
                    v = vt.render(self._org_hostvars[hostname])

                    self._hostvars[hostname][self._args["prefix"]+k] = v
                            
        return self._hostvars

    def getGroups(self):
        args = self._args

        try:
             args['name']
        except:
            printErrorMessage("You must specify a groupname (name=...)")
            sys.exit(1)

        for hostname in self._org_hostvars:
            tgroupname = Template(self._args['name'])
            groupname = tgroupname.render(self._org_hostvars[hostname])
            try:
                self._hostgroups[groupname]
            except:
                self._hostgroups[groupname] = dict( hosts=[] )

            self._hostgroups[groupname]["hosts"].append(hostname)

        return self._hostgroups

    def help(self):
        return """mod_static.py help
module configuration:
There is no specific configuration of this module

hostvars configuration:
[static-hostvars]      name it however you want...
module             mandatory, name of the modules (static in this case)
description        optional, describe the datasource
prefix             optional, a prefix for every MariaDB field
applyto            mandatory, all, comma separated names or regex expression.
keyN               mandatory, provide the name for the key. N is an integer, and pairs with valueN with the same N value
valueN             mandatory, assign a value to keyN

groups configuration:
[static-groups]    name it however you want...
module             mandatory, name of the modules (static in this case)
enabled            optional, whether the config is enabled or not (defaults to enabled)
name               Really clever name for your group. Or a jinja2 templated name.

"""
