#!/bin/python -tt
# -*- coding: utf-8 -*-

# author: William Leemans <willie@elaba.net>
# copyright: Copyright 2015, William Leemans
# license: GPL v3


import os
import sys
import json
import iniparse
from jinja2 import Template
from optparse import OptionParser
from time import gmtime, strftime


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

    print json.dumps( inventory, sort_keys=True, indent=4, separators=(',',': ') )
    sys.exit()


def showModuleHelp( config, modulename ):
    sys.path.append(config["path"]["modules"])
    print config["path"]["modules"] + "/mod_%s.py" %modulename
    if not os.path.isfile(config["path"]["modules"] + "/mod_%s.py" %modulename):
        printErrorMessage( "Thr module %s doesn't exist." % modulename)
        sys.exit()

    exec "import mod_%s" % modulename
    exec "res = mod_%s.mod_%s(config)" % (modulename, modulename )
    print res.help()

   
def refreshCache( config ):
    printVerboseMessage("Refreshing cache...")
    inventory = getInventory( config )
    cache_file = config["path"]["cache"] + "/inventory." + strftime(config["general"]["cache_timestamp"], gmtime())
    cache_link = config["path"]["cache"] + "/inventory.latest"
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
    for d in config["hostvars"]["priority"]:
        parse_definition = False
        if hostvarscfg[d]["enabled"]:
            try:
                 modulescfg[hostvarscfg[d]["module"]]
            except:
                 args = dict()
            else:
                args = modulescfg[hostvarscfg[d]["module"]].copy()
            args.update(hostvarscfg[d])
            exec "res = mod_%s.mod_%s(config, args, hostvars)" % (hostvarscfg[d]["module"], hostvarscfg[d]["module"])
            hostvars = joinHostvars(hostvars, res.getHostvars())
    
    inventory.update({ "_meta": dict( { "hostvars": hostvars } ) })

    required_groups_modules = [ groupscfg[g]["module"] for g in config["groups"]["priority"] ]
    list( set(required_groups_modules) )

    for m in required_groups_modules:
        exec "import mod_%s" % m

    hostgroups = dict()
    for group in config["groups"]["priority"]:
        if groupscfg[group]["enabled"]:
            try:
                modulescfg[groupscfg[group]["module"]]
            except:
                args = dict()
            else: 
                args = modulescfg[groupscfg[group]["module"]].copy()
            args.update(groupscfg[group])
            exec "res = mod_%s.mod_%s(config, args, hostvars)" % (groupscfg[group]["module"], groupscfg[group]["module"])
            hostgroups = joinGroups(hostgroups, res.getGroups())

    for group in hostgroups:
        inventory.update( { group : hostgroups[group]} )

    return inventory


def getCache( config ):
    printVerboseMessage("Getting cache")
    latest_cache_file = config["path"]["cache"] + "/inventory.latest"
    if not os.path.isfile(latest_cache_file):
        printErrorMessage( "There is no cache available.")
        printErrorMessage( "Please rerun lisa using the --refresh-cache option")
        sys.exit()
    
    with open(latest_cache_file) as json_file:
        data = json.load(json_file)
    return data


def joinGroups( target, source ):
    newlist = dict()
    parsed = list()
    for groupname in target:
        try:
            source[groupname]
            newlist[groupname]
        except:
            newlist.update( { groupname: target[groupname] } )
        else:
            parsed.append(groupname)
            target[groupname].update(source[groupname])
            newlist[groupname].update(source[groupname])

    for groupname in source:
        if groupname not in parsed:
            newlist.update( {groupname: source[groupname]} )

    return newlist

def joinHostvars( target, source ):
    parsed = list()
    not_parsed = list()
    newlist = dict()
    for hostname in target:
        try:
            source[hostname]
        except:
            newlist.update( {hostname: target[hostname]} )
        else:
            parsed.append(hostname)
            target[hostname].update(source[hostname])
            newlist.update( {hostname: target[hostname]} )

    for hostname in source:
        if hostname not in parsed:
            newlist.update( {hostname: source[hostname]} )

    return newlist

def printVerboseMessage( message ):
    global verbose
    if verbose:
        print >> sys.stderr, message

def printErrorMessage( message ):
    print >> sys.stderr, message
          
def getConfig():
    global path_config
    printVerboseMessage("Checking and loading configuration")
    config = dict( 
        hostvars = dict(
            priority = []
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
        printErrorMessage("Could not find the config file: %s" % path_config + "/config.ini")
        sys.exit(1)
    with open(path_config + "/config.ini") as ini_file:
        ini = iniparse.INIConfig(ini_file)

    if type(ini["hostvars"]) is iniparse.ini.INISection:
        if type(ini["hostvars"]["priority"]) is str:
            config["hostvars"]["priority"] = [ el.strip(" ") for el in ini["hostvars"]["priority"].split(",") ]
    config["hostvars"]["priority"].reverse()

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
            printErrorMessage( "the %s path option in config.ini doesn't exist!" % p)
            sys.exit()
    
    if type(ini["files"]) is iniparse.ini.INISection:
        if type(ini["files"]["hostvars"]) is str:
            config["files"]["hostvars"] = ini["files"]["hostvars"]
        if type(ini["files"]["groups"]) is str:
            config["files"]["groups"] = ini["files"]["groups"]
        if type(ini["files"]["modules"]) is str:
            config["files"]["modules"] = ini["files"]["modules"]
    for f in config["files"]:
        if config["files"][f][0] != "/":
            config["files"][f] = path_config + "/" + config["files"][f]
        config["files"][f] = os.path.realpath(config["files"][f])
        if not os.path.isfile(config["files"][f]):
            printErrorMessage( "the %s file option in config.ini doesn't exist!" % f)
            sys.exit()
    printVerboseMessage("Configuration checking done")
    return config


def getHostvarsConfig( config ):
    printVerboseMessage("Get hostvars configuration")
    config = ini2dict(config["files"]["hostvars"])
    for section in config:
        try:
            config[section]["enabled"]
        except:
            config[section]["enabled"] = True
        else:
            if config[section]["enabled"].lower() == "true" or config[section]["enabled"].lower() == "yes" or config[section]["enabled"] == "1":
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
    config = ini2dict(config["files"]["modules"])
    return config


def getGroupsConfig( config ):
    printVerboseMessage("Get groups configuration")
    config = ini2dict(config["files"]["groups"])
    for section in config:
        try:
            config[section]["enabled"]
        except:
            config[section]["enabled"] = True
        else:
            if config[section]["enabled"].lower() in ["true", "yes", "1"]:
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
    parser.add_option("-v", "--verbose", dest="verbose", help="Be verbose", action="store_true", default=False)
    parser.add_option("-r", "--refresh-cache", dest="refresh_cache", help="Refresh the cache file if used (see config.ini)", action="store_true", default=False)
    parser.add_option("", "--module-help", dest="module_help", help="Show help for a module", action="store", default=None)

    (options, args) = parser.parse_args()

    verbose = options.verbose

    return options
    
if __name__ == '__main__':
    main()

