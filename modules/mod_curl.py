#!/bin/python -tt
# -*- coding: utf-8 -*-
# vim: tabstop=12 expandtab shiftwidth=4 softtabstop=4

# author: William Leemans <willie@elaba.net>
# copyright: Copyright 2015, William Leemans
# license: GPL v3

import pycurl
import sys
from io import BytesIO
import json
import csv

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
        buffer = BytesIO()
        con = pycurl.Curl()
        con.setopt(con.URL, self._args["url"])
        con.setopt(con.WRITEFUNCTION, buffer.write)
        con.perform()
        rc = con.getinfo(con.RESPONSE_CODE)
        con.close()
        self._convert(buffer.getvalue())
        self._add_prefix()
        return self._hostvars

    def _add_prefix(self):
        try:
            self._args["prefix"]
        except:
            self._args["prefix"] = ""

        new_hostvars = dict()
        for hostname in self._hostvars:
            nf = dict()
            for fact in self._hostvars[hostname]:
                nf.update({self._args["prefix"] + fact: self._hostvars[hostname][fact]})
            new_hostvars.update({hostname: nf})
        self._hostvars = new_hostvars
            

    def _convert(self, value):
        try:
            self._args["format"]
        except:
            self._args["format"] = "json"

        if self._args["format"] == "json":
            self._hostvars = json.loads(value)

        elif self._args["format"] == "csv":
            try:
                self._args['header']
            except:
                self._args['header'] = ""

            try:
                self._args['exclude']
            except:
                self._args['exclude'] = ""

            try:
                self._args['delimiter']
            except:
                self._args['delimiter']=","

            try:
                self._args['quotechar']
            except:
                self._args['quotechar']=""

            header = []
            exclude = []

            if self._args['header'] != "":
                headerIO = BytesIO(self._args['header'])
                headerRDR = csv.reader(headerIO, delimiter=self._args['delimiter'], quotechar=self._args['quotechar'])
                for row in headerRDR:
                    header = row
                    break

                if 'hostname' not in header:
                    printErrorMessage("Your header must contain 'hostname'")
                    sys.exit(1)
                hostname_field = header.index('hostname')
            
            if self._args['exclude'] != "":
                excludeIO = BytesIO(self._args['exclude'])
                excludeRDR = csv.reader(excludeIO, delimiter=self._args['delimiter'], quotechar=self._args['quotechar'])
                for row in excludeRDR:
                    exclude = list(set(row))
                    break

                nexclude = []
                for el in exclude:
                    if el != 'hostname' and el in header :
                        nexclude.append(el)
                exclude = nexclude[:]

            res = dict()

            valueIO = BytesIO(value)
            valueRDR = csv.reader(valueIO, delimiter=self._args['delimiter'], quotechar=self._args['quotechar'])
            for row in valueRDR:
                if len(row) == len(header):
                    thostvars = { row[hostname_field]: dict(zip(header, row)) }
                    for el in exclude:
                        del thostvars[row[hostname_field]][el]
                    res.update( thostvars )
            self._hostvars = res


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
format             optional, format the result is in. Currently supports json and csv (defaults to json)
header             optional, a csv list of fields the url will yield. Only for csv
exclude            optional, don't parse the fields matching this comma separated list of fieldnames

groups configuration: (TBD)
[curl-groups]    name it however you want...
module             mandatory, name of the modules (curl in this case)
enabled            optional, whether the config is enabled or not (defaults to enabled)
url                mandatory, URL to get 
format             optional, format the result is in currently supports json and csv (defaults to json)
"""
