#!/bin/python -tt
# -*- coding: utf-8 -*-

# author: William Leemans <willie@elaba.net>
# copyright: Copyright 2015, William Leemans
# license: GPL v3

import os
import sys
import MySQLdb
import MySQLdb.cursors

class mod_mariadb():
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
        db_config = self._getDBconfig("hostvars")
        conn = MySQLdb.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(self._getQuery())
        for rec in cursor.fetchall():
            temp = dict()
            for el in rec:
                temp.update({ self._args["prefix"] + el: rec[el] })
            self._hostvars.update( { rec[self._args['index']]: temp } )
        cursor.close()
        conn.close()
        return self._hostvars

    def getGroups(self):
        db_config = self._getDBconfig("groups")
        conn = MySQLdb.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(self._getQuery())
        fields = [i[0] for i in cursor.description]
        if len(fields) < 2:
            printErrorMessage( "Your group query doesn't contain at least 2 fields: the groupname, and hostname")
            sys.exit(1)
        for rec in cursor.fetchall():
            try:
                self._hostgroups[rec[fields[0]]]
            except:
                self._hostgroups[rec[fields[0]]] = dict( hosts=list() )

            self._hostgroups[rec[fields[0]]]["hosts"].append(rec[fields[1]])
        
        cursor.close()
        conn.close()
        return self._hostgroups

    def _getQuery( self ):
        args = self._args
        try:
            args["query"]
        except:
            query = False
        else:
            query = True

        try:
            args["query_file"]
        except:
            if not query:
                printErrorMessage( "query or query_file should be defined.")
                sys.exit(1)
        else:
            if args["query_file"] == "/":
                args["query"] = self._loadSQLfile(args["query_file"])
            else:
                args["query_file"] = os.path.realpath(self._config["path"]["working"] + "/" + args["query_file"])
                args["query"] = self._loadSQLfile(args["query_file"])

        return args["query"]

    def _loadSQLfile( self, filename ):
       if not os.path.isfile(filename):
           printErrorMessage( "File %s cannot be found!" % filename)
           sys.exit()
       else:
           with open( filename ) as f:
              r = f.read()
           return r

    def _getDBconfig(self, vartype):
        args = self._args
        db_config = dict(
            db = args['db'],
            cursorclass = MySQLdb.cursors.DictCursor,
            charset = 'utf8',
            use_unicode = True
        )
        try:
            args['host']
        except:
            db_config["host"] = "localhost"
        else:
            db_config["host"] = args['host']

        try:
            int(args['port'])
        except:
            db_config["port"] = 3306
        else:
            db_config["port"] = int(args['port'])

        try:
            args["user"]
        except:
            printErrorMessage( "You must add a user to connect to the MariaDB host (user=...)")
            sys.exit(1)
        else:
            db_config["user"] = args["user"]

        try:
            args['password']
        except:
            printErrorMessage("You haven't specified a password for the MariaDB user (password=...)")
            sys.exit(1)
        else:
            db_config["passwd"] = args['password']
        
        try:
            args['db']
        except:
            printErrorMessage("You haven't specified a MariaDB dB (db=...)")
            sys.exit(1)
        else:
            db_config["db"] = args['db']
        if vartype == "hostvars":
            try:
                args['index']
            except:
                printErrorMessage("You must specify an index for the results to be parsed (index=...)")
                sys.exit()

        return db_config

    def help(self):
        return """mod_mariadb.py help
module configuration:
[mariadb]
user               MariaDB user
password           MariaDB user password
host               MariaDB hostname
db                 MariaDB database
port               MariaDB port

hostvars configuration:
[hostvars-definition]  name your hostvars config
module             mandatory, name of the modules (mariadb in this case)
query_file         mandatory if query isn't provided. The path to a sql file containing the SQL query
query              mandatory if query_file isn't provided. the SQL query to be executed.
index              mandatory, the MariaDB field that contains the hostname
description        optional, describe the datasource
user               optional, MariaDB user
password           optional, MariaDB user password
host               optional, MariaDB hostname
db                 optional, MariaDB database
port               optional, MariaDB port
prefix             optional, a prefix for every MariaDB field

groups configuration:
[groups-definition]  name your group
module             mandatory, name of the modules (mariadb in this case)
query_file         mandatory if query isn't provided. The path to a sql file containing the SQL query
query              mandatory if query_file isn't provided. the SQL query to be executed.
description        optional, describe the datasource
user               optional, MariaDB user
password           optional, MariaDB user password
host               optional, MariaDB hostname
db                 optional, MariaDB database
port               optional, MariaDB port

"""
