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

"""
This component is pretty lame, because we translate text to python objects, sent them to pymongo which converts it back to the pretty same text representation as the input data. We do it for the sake of simplicity and security, but we are not happy with the result.

TODO:
- make component work also with one database using subcollections eg. rather than using db.database.collection, using db.oneDB.rootColl,collection. It saves space and the security layer is here so we don't need to rely on Mongo's own approach to users.
"""

from ACR.utils import replaceVars, str2obj, dicttree
from ACR.components import *
from ACR.utils.xmlextras import tree2xml
from xml.sax.saxutils import escape,unescape
import pymongo
from bson import objectid, errors
from ACR.utils.interpreter import makeTree
import time

STR_TYPES=(str,unicode)

class Mongo(Component):
	SERVER='localhost'
	PORT=27017
	DIRECTION="DESCENDING"
	def __init__(self,config):
		if not config:
			config={}
		server=config.get("server",self.SERVER)
		port=config.get("port",self.PORT)
		#self.conn=pymongo.Connection()
		#self.DEFAULT_DB=config.get("defaultdb")
		self.DEFAULT_COLL=config.get("defaultcoll")

	def replace(self,acenv,config):
		return self.update(acenv,config,replace=False)

	def update(self,acenv,config, replace=True):
		D=acenv.doDebug
		params=config["params"]
		coll=params["coll"]
		where=params["where"]
		o=params["spec"]
		if D:
			acenv.debug("where clause is %s",where)
			acenv.debug("update object is %s",o)
		try:
			# multi=True throws
			return coll.update(where, o, safe=True, multi=replace)
		except pymongo.errors.OperationFailure, e:
			return {
				"@status": "error",
				"@error": "NotUpdated",
				"@message": str(e)
			}

	def insert(self,acenv,config):
		D=acenv.doDebug
		params=config["params"]
		coll=params["coll"]
		o=params["spec"]
		if D: acenv.debug("doing %s",coll.insert)
		try:
			id=coll.insert(o,safe=True)
		except Exception,e:
			return {
				"@status":"error",
				"@error":str(e.__class__.__name__),
				"@message":str(e)
			}
		if D:acenv.info("inserted: %s",o)
		ret={"@id":str(id),"@status":"ok"}
		#leaving space for debugging and profiling info
		return ret

	def save(self,acenv,config):
		D=acenv.doDebug
		if D: acenv.debug("START Mongo.save with: %s", config)
		params=config["params"]
		coll=params["coll"]
		o=params["spec"]
		# if D: acenv.debug("doing %s",coll.insert)
		id=coll.save(o,safe=True)
		if D:acenv.debug("saved:\n%s",o)
		ret={
			"@status":"ok",
			"@id":id
		}
		#leaving space for debugging and profiling info
		return ret

	def remove(self,acenv,config):
		D=acenv.doDebug
		if D: acenv.debug("START Mongo.remove with: %s", config)
		params=config["params"]
		coll=params["coll"]
		o=params["spec"]
		if D: acenv.debug("doing %s",coll.insert)
		if o:
			lastError=coll.remove(o,safe=True)
		else:
			return {
				"@status":"error",
				"@error":"DataNotRemoved",
				"@message":"Empty object results in removal of all data. For safety this functionality is blocked here, please use removeAll command instead."
			}
		if D and not lastError:acenv.debug("removed:\n%s",o)
		#leaving space for debugging and profiling info
		return lastError or {"@status":"ok"}

	def removeAll(self,acenv,config):
		D=acenv.doDebug
		if D: acenv.debug("START Mongo.removeAll with: %s", config)
		coll=config["params"]["coll"]
		lastError=coll.remove({},safe=True)
		if D and not lastError:acenv.debug("removed:\n%s",o)
		# leaving space for debugging and profiling info
		return lastError or {"@status":"ok"}

	def count(self,acenv,config):
		return self.find(acenv,config,count=True)

	def findOne(self,acenv,config):
		return self.find(acenv,config,one=True)

	def find(self,acenv,config,count=False,one=False):
		D=acenv.doDebug
		P=acenv.doProfiling
		params=config["params"]
		coll=params["coll"]
		p={
			"spec":params["spec"]
		}
		if D:acenv.debug("Finding objects matching:\n%s",p["spec"])
		for i in params:
			#FIXME lame exception
			if type(params[i]) is list and i not in ['sort','spec']:
				params[i]=replaceVars(acenv,params[i])
		try:
			p["fields"]=params["fields"]
		except:
			pass
		if not one:
			try:
				p["skip"]=int(params["skip"])
			except: pass
			try:
				p["limit"]=int(params["limit"])
			except: pass
			try:
				p["sort"]=params["sort"]
			except: pass

		if P: t=time.time()
		if count:
			ret=coll.find(**p).count()
			if D:acenv.debug("Matching documents number: %s",ret)
		elif one:
			ret=list(coll.find(**p).limit(-1))
			ret=ret and ret[0] or None
			if ret:
				ret["_id"]=str(ret["_id"])
		else:
			ret=list(coll.find(**p))
			if ret and params.has_key("sort") and len(params["sort"]) is 1:
				sortBy=params['sort'][0][0]
				if ret[0].has_key(sortBy)\
					and type(ret[0][sortBy]) in STR_TYPES\
					or ret[-1].has_key(sortBy)\
					and type(ret[-1][sortBy]) in STR_TYPES:
					if D:acenv.debug("Doing additional Python sort")
					def sortedKey(k):
						try:
							return k[sortBy].lower()
						except:
							return ''
					pars={"key":sortedKey}
					if params['sort'][0][1] is pymongo.DESCENDING:
						pars["reverse"]=True
					ret=sorted(ret, **pars)

		if P:
			acenv.profiler["dbtimer"]+=time.time()-t
			acenv.profiler["dbcounter"]+=1
		if ret and type(ret) is list:
			for i in ret:
				try:
					i["_id"]=str(i["_id"])
				except KeyError:
					pass
			if D:acenv.debug("END Mongo.find with %s",ret)
			return ret #[e.set("_id", str(e["_id"])) and e for e in ret]
		else:
			if count:
				if D:acenv.debug("END Mongo.count with 0")
				return ret
			if D:acenv.debug("END Mongo.find with one or no object")
			return ret

	def getColls(self, acenv, config):
		return acenv.app.storage.collection_names()

	def generate(self, acenv, config):
		D=acenv.doDebug
		if D: acenv.debug("START Mongo: %s with %s", config["command"].split(":").pop(), config)
		db=acenv.app.storage
		cfg=config.copy()
		params=cfg["params"].copy()
		try:
			collName=params["coll"].execute(acenv)
			params["coll"]=acenv.app.storage[collName]
		except KeyError:
			pass
		try:
			where=params["where"].execute(acenv)
			where["_id"]=objectid.ObjectId(where["_id"])
			params["where"]=where
		except (errors.InvalidId, KeyError):
			# we are dealing with customized or no _id property
			pass
		spec=config["content"].execute(acenv)
		try:
			spec["_id"]=objectid.ObjectId(spec["_id"])
		except (errors.InvalidId, KeyError):
			# we are dealing with customized or no _id property
			pass
		params["spec"]=spec
		cfg["params"]=params
		return self.__getattribute__(config["command"].split(":").pop())(acenv, cfg)

	def parseAction(self,config):
		s=[]
		fields={}
		pars=config["params"]
		for elem in config["content"]:
			if type(elem) is tuple:
				if elem[0]=="where":
					pars["where"]=makeTree("".join(elem[2]))
				elif elem[0]=="field":
					fields[elem[1]["name"]]=bool(str2obj(elem[1]["show"]))
				else:
					pars[elem[0]]=(elem[1],elem[2])
			elif type(elem) is str:
				s.append(elem.strip())
		try:
			show=pars["show"].split(",")
			pars["fields"]=dict(map(lambda x: (x.strip(), 1), show))
		except KeyError:
			pass
		try:
			hide=pars["hide"].split(",")
			pars["fields"]=dict(map(lambda x: (x.strip(), 0), hide))
		except KeyError:
			pass
		try:
			# TODO bring back support for sub-collections - .split(".")
			coll=makeTree(pars["coll"])#.split(".")
			pars["coll"]=coll
		except KeyError:
			if config["command"]!="getColls":
				raise Error("no coll parameter specified")
		try:
			sort=pars["sort"].split(",")
			directions=pars.get("direction",self.DIRECTION).split(",")
			directions=map(lambda x: pymongo.__dict__.get(x.upper()),directions)
			if len(directions)>=len(sort):
				pars["sort"]=zip(sort,directions)
			else:
				import itertools
				pars["sort"]=list(itertools.izip_longest(sort,directions,fillvalue=directions[-1]))
		except:
			pass

		return {
			"command":config["command"],
			"content":makeTree("".join(s) or {}),
			"params":pars
		}

def getObject(config):
	return Mongo(config)
