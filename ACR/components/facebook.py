#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Asyncode Runtime - enabling non-tech people to develop internet software.
# Copyright (C) 2014-2015 Asyncode Ltd.

# PROPRIETARY component

from ACR.components import *
from ACR.utils import generateID, replaceVars
from ACR.utils.interpreter import makeTree
from ACR import acconfig
from ACR.errors import Error
from ACR.session.mongoSession import MongoSession
import re,json
#http://www.gevent.org/intro.html
#from gevent import monkey; monkey.patch_socket()
from urllib2 import urlopen
from urlparse import parse_qs

V="v2.2"
API_URL="https://graph.facebook.com/"+V+"/"

class Facebook(Component):
        #defaults

        def __init__(self,config):
                cfg={}
                for i in config:
                        cfg[i[0]]=i[2][0]
                config=cfg
                if not config:
                        config={}
                self.server=config.get("appID")
                self.port=config.get("appSecret")

        def generate(self,acenv,conf):
                r=urlopen(API_URL+conf["params"]["url"].execute(acenv)).read()
                try:
                        return json.loads(r)
                except:
                        res=parse_qs(r, keep_blank_values=True)
                        for i in res:
                                res[i]=res[i][0]
                        return res

        def parseAction(self,config):
                s=[]
                fields={}
                pars=config["params"]
                for elem in config["content"]:
                        if type(elem) is tuple:
                                if elem[0]=="where":
                                        pars["where"]=makeTree("".join(elem[2]))
                                #deprecated
                                elif elem[0]=="field":
                                        fields[elem[1]["name"]]=bool(str2obj(elem[1]["show"]))
                                else:
                                        pars[elem[0]]=(elem[1],elem[2])
                        elif type(elem) is str:
                                s.append(elem.strip())
                for i in pars:
                        pars[i]=makeTree(pars[i])

                return {
                        "command":config["command"],
                        "content":"".join(s),
                        "params":pars
                }

def getObject(config):
        return Facebook(config)
