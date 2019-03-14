from mininet.net import Mininet
from mininet.node import Node
from mininet.topo import SingleSwitchTopo
from mininet.log import info, setLogLevel

from select import poll, POLLIN
from time import time

def chunks(l, n):
	return [l[i: 1+n] for i in range(0, len(l), n)]

def startattack(host, targetIPs):

	targetIPs = ' '.join(targetIPs)

	# Simple ping loop
	cmd = ('while true; do '
           ' for ip in %s; do ' % targetIPs +
           '  echo -n %s "->" $ip ' % host.IP() +
           '   `ping -w 1 $ip | grep packets` ;'
           ' done; '
           'done &'
		  )

	info( '*** Host %s (%s) will be pinging ips: %s\n' % (host.name, host.IP(), targetIPs))

	host.cmd(cmd)

def ping(netsize, chunksize, seconds):

	# Create network
	topo = SingleSwitchTopo(netsize)
	net = Mininet(topo = topo, waitConnected = True)
	net.start()
	hosts = net.hosts
	subnets = chunks(hosts, chunksize)

	fds = [host. stdout.fileno() for host in hosts]
	poller = poll()
	for fd in fds:
		poller.register(fd, POLLIN)

	for subnet in subnets:
		ips = [host.IP() for host in subnet]
		host = net.get('h1')
		# for host in subnet:
		startattack(host, ips)

	endTime = time() + seconds
	while time() < endTime:
		readble = poller.poll(1000)
		for fd, _mask in readble:
			node = Node.outToNode[fd]
			info('%s: ' % node.name, node.monitor().strip(), '\n')

	for host in hosts:
		host.cmd('kill %while')

	net.stop()

if __name__ == '__main__':
	setLogLevel('info')
	ping(netsize = 4, chunksize = 4, seconds = 60)