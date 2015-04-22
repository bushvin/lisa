#!/bin/python -tt
# -*- coding: utf-8 -*-
# vim: tabstop=12 expandtab shiftwidth=4 softtabstop=4

# author: William Leemans <willie@elaba.net>
# copyright: Copyright 2015, William Leemans
# license: GPL v3

import pycurl
from io import BytesIO
import json
#from StringIO import StringIO

#import sys
#import re
#from jinja2 import Template

class mod_curl():
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
            self._args["json"]
        except:
            self._args["format"] = "json"

        buffer = BytesIO()
        con = pycurl.Curl()
        con.setopt(con.URL, self._args["url"])
        con.setopt(con.WRITEFUNCTION, buffer.write)
        con.perform()
        rc = con.getinfo(con.RESPONSE_CODE)
        con.close()
        self._hostvars = self._convert(buffer.getvalue(), self._args["format"])

        return self._hostvars

    def _convert(self, value, format):
        if format == "json":
            return json.loads(value)
        else:
            return {}

    def getGroups(self):
        try:
            self._args["json"]
        except:
            self._args["format"] = "json"

        buffer = BytesIO()
        con = pycurl.Curl()
        con.setopt(con.URL, self._args["url"])
        con.setopt(con.WRITEFUNCTION, buffer.write)
        con.perform()
        rc = con.getinfo(con.RESPONSE_CODE)
        con.close()
        self._hostgroups = self._convert(buffer.getvalue(), self._args["format"])

        return self._hostgroups

    def help(self):
        return """mod_curl.py help
module configuration:
There is no specific configuration of this module

hostvars configuration:
[curl-hostvars]      name it however you want...
module             mandatory, name of the modules (curl in this case)
description        optional, describe the datasource
url                mandatory, URL to get 
format             optional, format the result is in (defaults to json)

groups configuration: (TBD)
[curl-groups]    name it however you want...
module             mandatory, name of the modules (curl in this case)
enabled            optional, whether the config is enabled or not (defaults to enabled)
url                mandatory, URL to get 
format             optional, format the result is in (defaults to json)
"""
