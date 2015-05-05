#!/bin/python -tt
# -*- coding: utf-8 -*-
# vim: tabstop=12 expandtab shiftwidth=4 softtabstop=4

# author: William Leemans <willie@elaba.net>
# copyright: Copyright 2015, William Leemans
# license: GPL v3

import pycurl
import os,sys
from io import BytesIO
import json
import csv
from urlparse import urlparse
import re

try:
    import xlrd
except:
    print "Please install the xlrd module"
    print "URL: https://pypi.python.org/pypi/xlrd"
    sys.exit(1)


class mod_uri():
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
            self._args["uri"]
        except:
            printErrorMessage("You haven't specified a uri")
            sys.exit(1)

        try:
            self._args["format"]
        except:
            self._args["format"] = "json"

        if self._args["format"] == "json":
            self._hostvars = self._convert_json()

        elif self._args["format"] == "csv":
            self._hostvars = self._convert_csv()

        elif self._args["format"] == "xls":
            self._hostvars = self._convert_xls()

        else:
            self._hostvars = {}


        self._add_prefix()
        return self._hostvars

    def _get_local_file_contents(self, path):
        if os.path.isfile(path):
            with open(path,'r') as f:
                data = f.read()
        else:
            printErrorMessage("The path specified (%s) is invalid." % path)
            sys.exit(1)
        return data

    def _get_http_file_contents(self, url):
        buffer = BytesIO()
        con = pycurl.Curl()
        con.setopt(con.URL, url)
        con.setopt(con.WRITEFUNCTION, buffer.write)
        con.perform()
        rc = con.getinfo(con.RESPONSE_CODE)
        con.close()
        if rc == 200:
            data = buffer.getvalue()
        else:
            printErrorMessage("There was an error retrieving data from %s. RC: %s" % (url, rc))
            sys.exit(1)
        return data


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
            
    def _csvline2list(self, value):
        reader = csv.reader(BytesIO(value), delimiter=self._args['delimiter'], quotechar=self._args['quotechar'])
        res = []
        for row in reader:
            res = row
            break

        return res

    def _get_url(self, res):
        url = ""
        if res.scheme != "":
            url = url + res.scheme + "://"
        if res.netloc != "":
            url = url + res.netloc
        if res.path != "":
            url = url + res.path
        return url

    def _convert_json(self):
        res = urlparse(self._args["uri"])
        if (res.scheme == "" and res.netloc == "") or res.scheme == "file":
            data = self._get_local_file_contents(res.path)

        elif (res.scheme == "" and res.netloc != "") or res.scheme == "http" or res.scheme == "https":
            data = self._get_http_file_contents(self._get_url(res))

        return json.loads(data)

    def _convert_csv(self):
        res = urlparse(self._args["uri"])
        if (res.scheme == "" and res.netloc == "") or res.scheme == "file":
            data = self._get_local_file_contents(res.path)

        elif (res.scheme == "" and res.netloc != "") or res.scheme == "http" or res.scheme == "https":
            data = self._get_http_file_contents(self._get_url(res))

        value = data.split("\n")
        try:
            self._args['delimiter']
        except:
            self._args['delimiter'] = ","

        try:
            self._args['quotechar']
        except:
            self._args['quotechar'] = ""

        try:
            header = self._args['header'].split(',')
        except:
            if len(value) > 0:
                header = self._csvline2list(value.pop(0))
            else:
                header = []

        try:
            exclude = self._args['exclude'].split(',')
        except:
            exclude = []


        if 'hostname' not in header:
            printErrorMessage("Your header must contain 'hostname'")
            sys.exit(1)
        hostname_field = header.index('hostname')

        nexclude = []
        for el in exclude:
            if el != 'hostname' and el in header :
                nexclude.append(el)
        exclude = nexclude[:]

        res = dict()

        for line in value:
            line = self._csvline2list(line)
            if len(line) == len(header):
                line[hostname_field] = line[hostname_field].lower()
                thostvars = { line[hostname_field]: dict(zip(header, line)) }
                for el in exclude:
                    del thostvars[line[hostname_field]][el]
                res.update( thostvars )
        return res

    def _xlsrow2list(self, row):
        res = list()
        count = 0
        for el in row:
            if el.ctype == 2:
                value = float(el.value)
            elif el.ctype == 3:
                value = el.value
            elif el.ctype == 4:
                value = bool(el.value)
            else:
                value = el.value

            res.append(value)
            #res.append(row[el])
        return res

    def _convert_xls(self):
        res = urlparse(self._args["uri"])
        filter = dict()
        for el in self._args:
            if re.match(r'^filterkey[0-9]+$', el):
                key = self._args[el]
                value = self._args["filtervalue" + el[9:]]
                filter.update({key:r"^%s$" % value})

        try:
            self._args["sheet"]
        except:
            self._args["sheet"] = -1

        try:
            header = self._args["header"].split(',')
        except:
            self._args["header"] = ""
            header = list()

        try:
            exclude = self._args['exclude'].split(',')
        except:
            exclude = []

        try:
            if self._args["includes_header"].lower() in [ "yes", "1", "true" ]:
                self._args["includes_header"] = True
            else:
                self._args["includes_header"] = False
        except:
            self._args["includes_header"] = False

        if (res.scheme == "" and res.netloc == "") or res.scheme == "file":
            ret = dict()

            if os.path.isfile(res.path):
                book = xlrd.open_workbook(res.path)
                if self._args["sheet"] == -1:
                    self._args["sheet"] = book.sheet_names()[0]
                sheet = book.sheet_by_name(self._args["sheet"])
                row_count = -1
                while row_count < (sheet.nrows - 1):
                    row_count = row_count + 1
                    if (self._args["header"] == "" or self._args["includes_header"]) and row_count == 0:
                        if len(header) == 0:
                            theader = self._xlsrow2list(sheet.row(row_count))
                            header = list()
                            for el in theader:
                                header.append(el.replace(" ","_"))
                        hostname_field = header.index('hostname')
                        nexclude = []
                        for el in exclude:
                            if el != 'hostname' and el in header :
                                nexclude.append(el)
                        exclude = nexclude[:]
                        nfilter = dict()
                        for el in filter:
                            if el in header:
                                nfilter.update({el:filter[el]})
                        filter = nfilter
                        print filter
                    else:
                        line = self._xlsrow2list(sheet.row(row_count))
                        while len(line) > len(header):
                            del line[-1]

                        while len(header) > len(line):
                            line.append("")
                        line[hostname_field] = line[hostname_field].lower()
                        thostvars = { line[hostname_field]: dict(zip(header, line)) }
                        remove = False
                        for el in filter:
                            if re.match(filter[el], thostvars[line[hostname_field]][el]) is None:
                                remove = True
                        if remove is True:
                            continue
                        for el in exclude:
                            del thostvars[line[hostname_field]][el]
                        ret.update( thostvars )
                return ret



        elif (res.scheme == "" and res.netloc != "") or res.scheme == "http" or res.scheme == "https":
            printErrorMessage("Haven't tried a url yet...")
            sys.exit(1)
            data = self._get_http_file_contents(self._get_url(res))

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
uri                mandatory, URi to get 
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
