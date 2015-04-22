#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Asyncode Runtime - XML framework allowing developing internet
# applications without using programming languages.
# Copyright (C) 2008-2010  Adrian Kalbarczyk

# This program is free software: you can redistribute it and/or modify
# it under the terms of the version 3 of GNU General Public License as published by
# the Free Software Foundation.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from ACR import acconfig
from ACR.utils import mail,replaceVars,prepareVars
from ACR.components import *
from ACR.errors import *
import os
import re
#from ACR.utils import dicttree,PREFIX_DELIMITER,getStorage,RE_PATH
from ACR.utils import json_compat as json
import oauth2 as oauth
from rauth import OAuth1Service

API_URL="https://api.twitter.com/1.1/"

class Twitter(Component):
        def __init__(self,config):
        #       raise Exception(config[0][2])                                                                                      
                if not config:                                                                                                     
                        raise Exception("Twitter component config not found.")                                                     
                self.CONSUMER_KEY=config[0][2][0]                                                                                  
                self.CONSUMER_SECRET=config[1][2][0]                                                                               
                self.twitter = OAuth1Service(                                                                                      
                        consumer_key=self.CONSUMER_KEY,                                                                            
                        consumer_secret=self.CONSUMER_SECRET,                                                                      
                        name='twitter',
                        access_token_url='https://api.twitter.com/oauth/access_token',
                        authorize_url='https://api.twitter.com/oauth/authorize',
                        request_token_url='https://api.twitter.com/oauth/request_token',
                        base_url='https://api.twitter.com/1.1/')

        def create_link(self,acenv,config):
                params=config["params"].copy()
                del params["key"]
                del params["secret"]
                return API_URL+config["command"].split(":").pop()+"?"+"&".join(map(lambda x: x[0]+"="+str(replaceVars(acenv,x[1])),params.items()))

        def oauth_req(self,url, key, secret, http_method="GET", post_body=None, http_headers=None):
                consumer = oauth.Consumer(key=self.CONSUMER_KEY, secret=self.CONSUMER_SECRET)
                token = oauth.Token(key=key, secret=secret)
                client = oauth.Client(consumer, token)

                resp, content = client.request(
                        url,
                        method=http_method,
                        body=post_body,
                        headers=http_headers,
                        force_auth_header=True
                )
                return json.json.loads(content)

        def login(self,acenv,conf):
                request_token, request_token_secret=self.twitter.get_request_token(params={"oauth_callback":replaceVars(acenv,conf["callback"])})

                return {
                        "request_token":request_token,
                        "request_token_secret":request_token_secret,
                        "authorize_url":self.twitter.get_authorize_url(request_token)
                }

        def accessToken(self,acenv,conf):
                session=self.twitter.get_auth_session(replaceVars(acenv,conf["request_token"]), replaceVars(acenv,conf["request_token_secret"]), data={'oauth_verifier': replaceVars(acenv,conf["verifier"])})
                return {
                        "token":session.access_token,
                        "secret":session.access_token_secret
                }

#       def raw(self,acenv,conf):
#               key=replaceVars(acenv,conf["key"])
#               secret=replaceVars(acenv,conf["secret"])
#               url=replaceVars(acenv,conf["url"])
#               return self.oauth_req(url+cursor,key,secret)

        def raw(self,acenv,conf):
                r=[]
                key=replaceVars(acenv,conf["key"])
                secret=replaceVars(acenv,conf["secret"])
                url=replaceVars(acenv,conf["url"])
                cursor=""
                try:
                        while True:
                                a=self.oauth_req(url+cursor,key,secret)
                                r.extend(a["users"])
                                if a["next_cursor"]!=0:
                                        cursor="&cursor="+str(a["next_cursor"])
                                else:
                                        break
                except:
                        pass
                return r

        def chunks(self,l, n):
                for i in xrange(0, len(l), n):
                        yield l[i:i+n]

        def generate(self,acenv,config):
                if config["command"] in ["raw", "login", "accessToken"]:
                        return self.__getattribute__(config["command"].split(":").pop())(acenv,config["params"])
                params=config["params"]
                multi=False
                for k in params:
                        params[k]=replaceVars(acenv,params[k])
                        if type(params[k]) is list:
                                if multi:
                                        raise Error("Twitter commands support only one value that is an array!")
                                multi=k
                links=[]
                if multi:
                        pagelen=params["page"]
                        del params["page"]
                        conf=config.copy()
#                       return [params[multi],self.chunks(params[multi][:1500],int(pagelen))]
                        for k in self.chunks(params[multi][:1500],int(pagelen)):
                                pars=params.copy()
                                pars[multi]=",".join(map(str,k))
                                conf["params"]=pars
                                links.append(self.create_link(acenv,conf))
                else:
                        links=self.create_link(acenv,config)
#               return links
                r=[]
                i=0
                #MAKE IT A GENERATOR!!!
                for l in links:
                        r.extend(self.oauth_req(l,config["params"]["key"],config["params"]["secret"]))
                        i=+1
                return r

        def parseAction(self,conf):
#               try:
#                       conf["params"]["url"]
#               except KeyError:
#                       raise Error("execNotSpecified", "'url' should be specified")
                params=conf["params"]
                for i in params:
                        if params[i]:
                                params[i]=prepareVars(params[i])
                conf["params"]=params
                return conf

def getObject(config):
        return Twitter(config)
