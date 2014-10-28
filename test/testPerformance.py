import time

N=1000000

def x(g,n):
	for i in xrange(n):
		g.next()
	return g.next()
g=iter([1,2,3,4,5,6,7,8,9,10,11])
#print x(g,10)
#print dir(g)

time1 = time.time()
for i in xrange(N):
	g=iter([1,2,3,4,5,6,7,8,9,10,11])
	x(g,10)
time2 = time.time()
print 'time 1', time2-time1

def y(g,n):
	j=0
	for i in g:
		if j is n-1:
			return g.next()
		j+=1
g=iter([1,2,3,4,5,6,7,8,9,10,11])

#print y(g,10)
time1 = time.time()
for i in xrange(N):
	g=iter([1,2,3,4,5,6,7,8,9,10,11])
	#y(g,10)
time2 = time.time()
print 'time 2', time2-time1
exit()
import types
def flatten(fragment,skip=False):
	def rec(frg):
		dtype=type(frg)
		if dtype is list:
			for i in frg:
				for j in rec(i):
					yield j
		elif dtype is dict:
			yield frg
			for i in frg.iteritems():
				for j in rec(i[1]):
					yield j
	g=rec(fragment)
	if skip:
		for i in xrange(skip):
			g.next()
	for i in g:
		yield i

d=[{"a":1,"b":{"x":2}},{"y":3},[{"a":4}]]
#d={"a":1,"b":{"x":2}}
f=flatten(d,52)

print type(f) is types.GeneratorType
print list(f)
def x():
	yield 1
	yield 2
	yield 3
def getNth(g,n):
	if type(n) is not int:
		raise TypeError("list indices must be integers, not %s"%type(n).__name__)
	j=0
	for i in g:
		if j is n:
			return i
		j+=1
	raise IndexError("generator index out of range")
print getNth(x(),'aaa')
print []['aaa']
