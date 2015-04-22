#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Properitary
# Copyright (C) 2014  Asyncode

from ACR import acconfig
from ACR.components import *
from ACR.components.interpreter import makeTree
from ACR.errors import *
from ACR.utils import HTTP
import os
import subprocess
import shutil
from bson import ObjectId

def exe(command):
	try:
		p=subprocess.Popen(command.split(), bufsize=2024, stdin=subprocess.PIPE,stdout=subprocess.PIPE)
	except OSError:
		raise Error("SubProcessError","%s failed with error code %s"%(command,res))
	# p.stdin.write(conf["content"])
	p.stdin.close()
	return p.stdout.read()

class ACP(Component):
	PROJECTS_PATH="/var/apps/"
	GIT_PATH="/home/ubuntu/git/"

	def __init__(self,config):
		currPath="/"
		for d in self.PROJECTS_PATH.split("/")[:-1]:
			currPath=os.path.join(currPath, d)
			if not os.path.isdir(currPath):
				os.mkdir(currPath)

	def isAvailable(self,acenv,config):
		name=config["name"].execute(acenv)
		return not os.path.isdir(self.PROJECTS_PATH+name+".asyncode.com")

	def create(self,acenv,config):
		if not self.isAvailable(acenv,config):
			return {
				"@status":"error",
				"@error":"NameTaken"
			}
		name=config["name"].execute(acenv)
		template=config["template"].execute(acenv)
		r={}
		savedPath = os.getcwd()
		os.chdir(self.GIT_PATH+template)
		r["gitPull"]=str(exe("git pull"))
		os.chdir(savedPath)
		try:
			shutil.copytree(self.GIT_PATH+template, self.PROJECTS_PATH+name+".asyncode.com")
		except OSError,e:
			pass
	#    return {
	#     "@status":"error",
	#     "@error":"NameNotAvailable",
	#     "@message":"Project name is not available."+str(e)
	#    }
		try:
			shutil.copytree(self.GIT_PATH+"IDEskel", self.PROJECTS_PATH+"ide."+name+".asyncode.com",symlinks=True)
		except OSError,e:
			pass
	#    return {
	#     "@status":"error",
	#     "@error":"NameNotAvailable",
	#     "@message":"Project name is not available."+str(e)
	#    }
	#  shutil.copyfile(self.GIT_PATH+"symlinktoIDE",self.PROJECTS_PATH+"ide."+name+".asyncode.com")
		conf=open(self.PROJECTS_PATH+"ide."+name+".asyncode.com/config.xml","w")
		conf.write("""<?xml version="1.0" encoding="UTF-8"?>
	<config>
	<!-- Core configuration -->
	 <name>%s</name>
	 <debug enable="f" level="debug"/>
	 <profiler enable="f"/>
	 <lang default="en"/>
	 <mongo db="%s_asyncode_com"/>
	 <timezone>UTC</timezone>
	 <component name="filesystem">
		<absolutePath>%s</absolutePath>
	 </component>
	</config>"""%(name,name,self.PROJECTS_PATH+name+".asyncode.com"))
		conf.close()
		user=acenv.app.storage.users.find({"_id":ObjectId(acenv.sessionStorage.data["ID"])})
		user=user[0]
		try:
			del user["_id"]
		except:
			pass
		try:
			del user["approvalKey"]
		except:
			pass
		try:
			del user["last_login"]
		except:
			pass
		user["loggedIn"]=False
		user["role"]="admin"
		acenv.app.storage.connection[name+"_asyncode_com"].users.insert(user)
		r.update({"@status":"ok"})
		return r

	def generate(self,env,config):
		return self.__getattribute__(config["command"].split(":").pop())(env,config["params"])

	def parseAction(self, conf):
		params={}
		for i in conf["params"]:
			params[i]=makeTree(conf["params"][i])
		ret=conf
		ret["params"]=params
		return ret

def getObject(config):
	return ACP(config)
