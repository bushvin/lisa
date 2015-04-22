#!/bin/python -tt
import xmlrpclib

class mod_static():
    _hostvars = dict()
    _config = dict()
    _args = dict()
    _org_hostvars = dict()

    def __init__( self, config=dict(), args=dict(), hostvars=dict() ):
        self._config = config
        self._args = args
        self._org_hostvars = hostvars

    def getHostvars(self):
        conn = xmlrpclib.Server('http://%s/rpc/api' % self._args["hostname"])
        session = conn.auth.login(self._args["user"], self._args["password"])
        hlist = conn.system.listSystems(session)
        # returns list( dict( last_checkin = DateTime, id= str, name= str) )

        return self._hostvars

    def help(self):
        return """mod_satellite.py help
datasource configuration:
[static_data]
module             mandatory, name of the modules (static in this case)
hostname           mandatory, hostname of the spacewalk/satellite server
user               mandatory, username of the spacewalk/satellite user
password           mandatory, password of the spacewalk/satellite user 
description        optional, describe the datasource
prefix             optional, a prefix for every MariaDB field
fields             optional, all or a comma sparated list of fields
"""

