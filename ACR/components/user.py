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

from ACR.components import *
from ACR.utils import generateID
from ACR.utils.interpreter import makeTree
from ACR import acconfig
from ACR.errors import Error
from hashlib import sha224
from ACR.session.mongoSession import MongoSession
import re

"""
	Users are stored in the Mongo:
	- email is required for now and acts as unique key until other login types will be implemented (uniquenes is handled here because Mongo does not support null - null is a value so only one object without email can exist),
	- password is sha2 of password; currently passing sha5 string directly from UA is not supported
	- role is for handling simple role-based privilege system,
	- privileges is a list of names of privileges granted to user,
	- approvalKey is key that user need to authorize his e-mail address (anty-spamm strategy and ensuring that user owns address)

--- Possible extensions ---

	- handling sha2 passwords directly from UA instead of hashing it here,
	- login via OpenID
	- OAuth
"""

class User(Component):
	#defaults
	ROLE="user"
	APPROVED=False
	MAIN=False
	EMAIL_RE=re.compile("^[a-zA-Z0-9._%-]+@[a-zA-Z0-9._%-]+.[a-zA-Z]{2,6}$")

	def login(self,acenv,conf):
		D=acenv.doDebug
		email=conf["email"].execute(acenv).lower()
		usersColl=acenv.app.storage.users
		try:
			user=list(usersColl.find({
				"email":email,
				'$or': [
					{'suspended': {'$exists': False}},
					{'suspended': False}
				]
			}))[0]
		except IndexError:
			if D: acenv.error("Account not found")
			return {
				"@status":"error",
				"@error":"AccountNotFound"
			}
		if "approvalKey" in user:
			return {
				"@status":"error",
				"@error":"EmailAddressNotVerified",
				"@message":"Email address is not verified."
			}

		password=conf["password"].execute(acenv)
		if user['password']==sha224(password).hexdigest():
			if D: acenv.info("Password is correct")
			if not acenv.sessionStorage:
				acenv.sessionStorage=MongoSession(acenv)
			if D: acenv.info("Setting session as:\n	%s",user)
			user["ID"]=str(user.pop("_id"))
			user["loggedIn"]=True
			acenv.sessionStorage.data=user
			return {"@status":"ok"}
		else:
			if D: acenv.error("Password is not correct")
			return {
				"@status":"error",
				"@error":"WrongPassword"
			}

	def approveEmail(self,acenv,conf):
		usersColl=acenv.app.storage.users
		if usersColl.update({"approvalKey":conf["key"].execute(acenv)},{"$unset":{"approvalKey":""}}, safe=True)["n"]>=1:
			return {"@status":"ok"}
		else:
			return {
				"@status":"error",
				"@error":"EmailAlreadyApproved",
				"@message":"Email address is already approved."
			}

	def logout(self,acenv,conf):
		try:
			acenv.sessionStorage.delete()
		except:
			pass
		return {"@status":"ok"}

	def register(self,acenv,conf):
		usersColl=acenv.app.storage.users
		email=conf["email"].execute(acenv).lower()
		if not (len(email)>5 and self.EMAIL_RE.match(email)):
			return {
				"@status":"error",
				"@error":"NotValidEmailAddress",
				"@message":"Suplied value is not a valid e-mail address"
			}
		if list(usersColl.find({"email":email})):
			return {
				"@status":"error",
				"@error":"EmailAdressAllreadySubscribed",
				"@message":"User already exists in the system"
			}
		key=generateID()
		d={
			"email":email,
			"password":sha224(conf["password"].execute(acenv)).hexdigest(),
			"role":conf.get("role") and conf["role"].execute(acenv) or self.ROLE,
			"approvalKey":key,
			"privileges":[]
		}
		if conf.has_key("data"):
			d.update(conf["data"].execute(acenv))
		id=usersColl.save(d,safe=True)
		return {
			"@status":"ok",
			"ID":str(id),
			"approvalKey":key
		}

	def generate(self,acenv,conf):
		return self.__getattribute__(conf["command"].split(":").pop())(acenv,conf)

	def parseAction(self,config):
		if config["command"] not in ["register","logout","login","approveEmail"]:
			raise Error("Bad command %s",config["command"])
		if config["command"] in ["register","login"] and not ("email" in config["params"].keys() or  "password" in config["params"].keys()):
			raise Error("Email or password is not set in %s action."%(config["command"]))

		ret={}
		for i in config["params"]:
			ret[i]=makeTree(config["params"][i])
		ret["command"]=config["command"]
		return ret

def getObject(config):
	return User(config)
