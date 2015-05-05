#!/usr/bin/python -tt
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# author: William Leemans <willie@elaba.net>
# copyright: Copyright 2015, William Leemans
# license: GPL v3


import iniparse
import json
import time
import os
import sys
from optparse import OptionParser

path_config = "."
verbose = False

def main():
    options = parse_args()

    path_working = os.path.realpath(os.path.dirname(__file__))
    config = getConfig()

    if options.module_help is not None:
        showModuleHelp(config, options.module_help)
        sys.exit()

    if options.refresh_cache:
        inventory = refreshCache(config)
    elif not config["general"]["use_cache"]:
        inventory = getInventory(config)
    else:
        inventory = getCache(config)

    if options.listinventory is True:
        print json.dumps( inventory, sort_keys=True, indent=4, separators=(',',': ') )
    elif options.showhost is not None:
        try:
            print json.dumps(inventory["_meta"]["hostvars"][options.showhost], sort_keys=True, indent=4, separators=(',',': '))
        except:
            print json.dumps({})
    else:
        print json.dumps({})
    sys.exit()

def showModuleHelp( config, modulename ):
    sys.path.append(config["path"]["modules"])
    print config["path"]["modules"] + "/mod_%s.py" %modulename
    if not os.path.isfile(config["path"]["modules"] + "/mod_%s.py" %modulename):
        printErrorMessage("The module %s doesn't exist." % modulename)
        sys.exit(1)

    exec "import mod_%s" % modulename
    exec "res = mod_%s.mod_%s(config)" % (modulename, modulename )
    try:
        print res.help()
    except AttributeError:
        print "There is no help for %s." % modulename

   
def refreshCache( config ):
    printVerboseMessage("Refreshing cache...")
    inventory = getInventory( config )
    cache_file = config["path"]["cache"] + "/lisa_inv." + time.strftime(config["general"]["cache_timestamp"], time.gmtime())
    cache_link = config["path"]["cache"] + "/lisa_inv.latest"
    with open( cache_file, "w" ) as f:
        f.write(json.dumps(inventory))
    if os.path.exists(cache_link):
        os.unlink(cache_link)
    os.symlink(os.path.basename(cache_file), cache_link)

    return inventory


def getInventory( config ):
    printVerboseMessage("Creating inventory")
    hostvarscfg = getHostvarsConfig(config)
    modulescfg  = getModulesConfig(config)
    groupscfg   = getGroupsConfig(config)

    inventory = dict()

    sys.path.append(config["path"]["modules"])
    required_hostvars_modules = [ hostvarscfg[d]["module"] for d in config["hostvars"]["priority"] ]
    list( set(required_hostvars_modules) )

    for m in required_hostvars_modules:
        exec "import mod_%s" % m

    hostvars = dict()
    for mod in config["hostvars"]["priority"]:
        if hostvarscfg[mod]["enabled"]:
            try:
                modulescfg[hostvarscfg[mod]["module"]]
            except:
                args = dict()
            else:
                args = modulescfg[hostvarscfg[mod]["module"]].copy()

            args.update(hostvarscfg[mod])
            starttime = int(round(time.time() *1000))
            exec "res = mod_%s.mod_%s(config, args, hostvars)" % (hostvarscfg[mod]["module"], hostvarscfg[mod]["module"])
            hostvars = joinHostvars(config, hostvars, res.getHostvars())
            endtime = int(round(time.time() *1000))
            printVerboseMessage("Creating hostvars using %s took %s miliseconds" % (mod, (endtime - starttime)))
    
    inventory.update({ "_meta": dict( { "hostvars": hostvars } ) })

    required_groups_modules = [ groupscfg[g]["module"] for g in config["groups"]["priority"] ]
    list( set(required_groups_modules) )

    for m in required_groups_modules:
        exec "import mod_%s" % m

    hostgroups = dict()
    for mod in config["groups"]["priority"]:
        if groupscfg[mod]["enabled"]:
            try:
                modulescfg[groupscfg[mod]["module"]]
            except:
                args = dict()
            else: 
                args = modulescfg[groupscfg[mod]["module"]].copy()
            args.update(groupscfg[mod])
            starttime = int(round(time.time() *1000))
            exec "res = mod_%s.mod_%s(config, args, hostvars)" % (groupscfg[mod]["module"], groupscfg[mod]["module"])
            hostgroups = joinGroups(hostgroups, res.getGroups())
            endtime = int(round(time.time() *1000))
            printVerboseMessage("Creating groups using %s took %s miliseconds" % (mod, (endtime - starttime)))

    for group in hostgroups:
        hostgroups[group]["hosts"].sort()
        inventory.update( { group : hostgroups[group]} )

    return inventory


def getCache( config ):
    printVerboseMessage("Getting cache")
    starttime = int(round(time.time() *1000))
    latest_cache_file = config["path"]["cache"] + "/lisa_inv.latest"
    if not os.path.isfile(latest_cache_file):
        printErrorMessage("There is no cache available.")
        printErrorMessage("Please rerun lisa using the --refresh-cache option")
        sys.exit(1)
    
    with open(latest_cache_file) as json_file:
        data = json.load(json_file)
    endtime = int(round(time.time() *1000))
    printVerboseMessage("Loading cache took %s miliseconds" % (endtime - starttime))
    return data


def joinGroups( target, source ):
    for groupname in source:
        try:
            target[groupname]
        except:
            target[groupname] = dict()

        target[groupname].update( source[groupname] )

    return target

def joinHostvars( config, target, source ):

    for hostname in source:
        try:
            target[hostname]
        except:
            if len(config["hostvars"]["facts"]) == 0:
                target[hostname] = dict()
            else:
                target[hostname] = dict()
                for el in config["hostvars"]["facts"]:
                    target[hostname][el] = "unknown"
            #target[hostname] = dict({ el: "unknown" } for el in config["hostvars"]["facts"])
        target[hostname].update( source[hostname] )

    return target

def printVerboseMessage( message ):
    global verbose
    if verbose:
        print >> sys.stderr, '\033[94m' +message+ '\033[m'

def printErrorMessage( message ):
    print >> sys.stderr, '\033[01;31m' +message+ '\033[m'
          
def getConfig():
    global path_config
    printVerboseMessage("Checking and loading configuration")
    config = dict( 
        hostvars = dict(
            priority = [],
            facts = []
        ),
        groups = dict(
            priority = []
        ),
        files = dict(
            hostvars = "hostvars.ini",
            groups = "groups.ini",
            modules = "modules.ini"
        ),
        general = dict(
            use_cache = False,
            cache_timestamp = "%Y%m%d%H%M%S"
        ),
        path = dict(
            working = path_config,
            cache = "cache",
            modules = "modules"
        )
    )
    if os.getenv("LISA_CONFIG") is not None:
        path_config = os.getenv("LISA_CONFIG")

    if not os.path.isfile(path_config + "/config.ini"):
        printErrorMessage("Could not find the config file: %s/config.ini" % path_config)
        sys.exit(1)
    with open(path_config + "/config.ini") as ini_file:
        ini = iniparse.INIConfig(ini_file)

    if type(ini["hostvars"]) is iniparse.ini.INISection:
        if type(ini["hostvars"]["priority"]) is str:
            config["hostvars"]["priority"] = [ el.strip(" ") for el in ini["hostvars"]["priority"].split(",") ]
            config["hostvars"]["priority"].reverse()
        if type(ini["hostvars"]["facts"]) is str:
            config["hostvars"]["facts"] = [ el.strip(" ") for el in ini["hostvars"]["facts"].split(",") ]

    if type(ini["groups"]) is iniparse.ini.INISection:
        if type(ini["groups"]["priority"]) is str:
            config["groups"]["priority"] = [ el.strip(" ") for el in ini["groups"]["priority"].split(",") ]
    config["groups"]["priority"].reverse()

    if type(ini["general"]) is iniparse.ini.INISection:
        if type(ini["general"]["use_cache"]) is str:
            if ini["general"]["use_cache"].strip(" ").lower() in ("yes", "true", "1"):
                config["general"]["use_cache"] = True
        if type(ini["general"]["cache_timestamp"]) is str:
            config["general"]["cache_timestamp"] = ini["general"]["cache_timestamp"]

    if type(ini["path"]) is iniparse.ini.INISection:
        if type(ini["path"]["cache"]) is str:
            config["path"]["cache"] = ini["path"]["cache"]
        if type(ini["path"]["modules"]) is str:
            config["path"]["modules"] = ini["path"]["modules"]
    for p in config["path"]:
        if config["path"][p][0] != "/":
            config["path"][p] = path_config + "/" + config["path"][p]
        config["path"][p] = os.path.realpath(config["path"][p])
        if not os.path.isdir(config["path"][p]):
            printErrorMessage("the %s path option in config.ini doesn't exist!" % p)
            sys.exit(1)
    
    if type(ini["files"]) is iniparse.ini.INISection:
        if type(ini["files"]["hostvars"]) is str:
            config["files"]["hostvars"] =  os.path.realpath(path_config + "/" + ini["files"]["hostvars"])
        if type(ini["files"]["groups"]) is str:
            config["files"]["groups"] =  os.path.realpath(path_config + "/" + ini["files"]["groups"])
        if type(ini["files"]["modules"]) is str:
            config["files"]["modules"] =  os.path.realpath(path_config + "/" + ini["files"]["modules"])
    printVerboseMessage("Configuration checking done")
    return config


def getHostvarsConfig( config ):
    printVerboseMessage("Get hostvars configuration")
    if not os.path.isfile(config["files"]["hostvars"]):
        printErrorMessage("%s could not be found." % config["files"]["hostvars"])
        sys.exit(1)

    config = ini2dict(config["files"]["hostvars"])
    for section in config:
        try:
            config[section]["enabled"]
        except:
            config[section]["enabled"] = True
        else:
            if config[section]["enabled"].lower() in ( "enabled", "true", "yes", "1" ):
                config[section]["enabled"] = True
            else:
                config[section]["enabled"] = False

        try:
            config[section]["module"]
        except:
            config[section]["module"] = ""

        try:
            config[section]["prefix"]
        except:
            config[section]["prefix"] = ""

    return config


def getModulesConfig( config ):
    printVerboseMessage("Get modules configuration")
    if not os.path.isfile(config["files"]["modules"]):
        printErrorMessage("%s could not be found." % config["files"]["modules"])
        sys.exit(1)

    config = ini2dict(config["files"]["modules"])
    return config


def getGroupsConfig( config ):
    printVerboseMessage("Get groups configuration")
    if not os.path.isfile(config["files"]["groups"]):
        printErrorMessage("%s could not be found." % config["files"]["groups"])
        sys.exit(1)

    config = ini2dict(config["files"]["groups"])
    for section in config:
        try:
            config[section]["enabled"]
        except:
            config[section]["enabled"] = True
        else:
            if config[section]["enabled"].lower() in ( "enabled", "true", "yes", "1" ):
                config[section]["enabled"] = True
            else:
                config[section]["enabled"] = False

        try:
            config[section]["module"]
        except:
            config[section]["module"] = ""

    return config


def ini2dict( filename ):
    with open( filename ) as ini_file:
        ini = iniparse.INIConfig(ini_file)
    s = dict()
    for section in ini:
        t = dict()
        for item in ini[section]:
            t.update( {item: ini[section][item].strip(" ")} )
        s.update( { section: t } )
    return s


def parse_args():
    global verbose
    usage = """Usage: %prog [options]
Additional configuration files:
config.ini (should be in the directory specified by path_config in %prog)
[general]
use_cache=yes|no
; optional, defaults to no
; can be activated to speed up lisa but make sure to execute lisa on 
; every change, or in a cron

cache_timestamp=%Y%m%d%H%M%S
; optional, defaults to %Y%m%d%H%M%S
; format: https://docs.python.org/2/library/time.html#time.strftime
; when using cache, lisa creates a cachefile. To keep track that
; cache's filename's extension is set to this

[path]
modules=modules
; optional, defaults to modules
; path where the modules can be found

cache=cache
; optional, defaults to cache
; path where the cache is stored

[files]
hostvars=hostvars.ini
; optional, defaults to hostvars.ini
; definition of data sources for the inventory

groups=groups.ini
; optional, defaults to groups.ini
; definition on how to group hosts

modules=modules.ini
; optional, defaults to modules.ini
; default configurations for the modules in use by the hostvars

[hostvars]
priority=infrastructure, static_data
; mandatory
; define the priority of the data source hostvars. 
; Host variables will be overwritten by "higher" prioritized variables

    """
    parser = OptionParser(usage=usage)
    parser.add_option("", "--list", dest="listinventory", help="List the entire inventory", action="store_true", default=False)
    parser.add_option("", "--host", dest="showhost", help="Show the hostvars for a specific host", action="store", default=None)

    parser.add_option("-v", "--verbose", dest="verbose", help="Be verbose", action="store_true", default=False)
    parser.add_option("-r", "--refresh-cache", dest="refresh_cache", help="Refresh the cache file if used (see config.ini)", action="store_true", default=False)
    parser.add_option("", "--module-help", dest="module_help", help="Show help for a module", action="store", default=None)

    (options, args) = parser.parse_args()

    verbose = options.verbose

    return options
    
if __name__ == '__main__':
    main()

