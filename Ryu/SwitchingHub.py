from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
import json

f = open("Logger.txt", 'w')

# To implement as a Ryu application, ryu.base.app_manager.RyuApp is inherited.
class SwitchingHub(app_manager.RyuApp):
	# Specifying the version of OpenFlow. In this case, it is OpenFlow1.3
	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
	
	def __init__(self, *args, **kwargs):
		super(SwitchingHub, self).__init__(*args, **kwargs)
		# Initialize MAC address table.
		self.mac_to_port = {}
		

	# The decorator specifies the event class supporting the received message and the state of the OpenFlow switch for the argument.
	@set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
	def switch_features_handler(self, ev):
		datapath = ev.msg.datapath
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		# Add the table-miss flow entry.
		match = parser.OFPMatch()
		actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
		self.add_flow(datapath, 0, match, actions)


	def add_flow(self, datapath, priority, match, actions):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		''' 
		Constrcut flow_mod message and send it:
			1. The OFPFlowMod message is used to modify flow entry messages. The controller sends this message to modify the flow entry table of the switch.
			2. OFPInstructionActions, this instruction writes/applies/clears the action.
			3. Using datapath.send_msg(mod) the controller sends the update flow messges.

		'''
		inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
		mod = parser.OFPFlowMod(datapath = datapath, priority = priority, match = match, instructions = inst)
		datapath.send_msg(mod)


	@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
	def packet_in_handler(self, ev):
		msg = ev.msg
		datapath = msg.datapath
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		# The datapath ID is used to identify OpenFlow switches. This helps by supporting multiple OpenFlow switch connections
		dpid = datapath.id
		self.mac_to_port.setdefault(dpid, {})

		pkt = packet.Packet(msg.data)
		eth_pkt = pkt.get_protocol(ethernet.ethernet)
		dst = eth_pkt.dst
		src = eth_pkt.src

		# Get the receive port from the OFPPacketIn match. The destination MAC address and source MAC address are obtained from the Ethernet header of the received packet.
		in_port = msg.match['in_port']

		# self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)
		f.write(json.dumps(self.mac_to_port))
		f.write("\n")

		# Learn a MAC address to avoid packet flooding next time. 
		self.mac_to_port[dpid][src] = in_port
		# print self.mac_to_port

		''' 
		First we check if we have the entry for that specific MAC address. If we do then we grab the value of the destination MAC address for the particular 
		source MAC address. Else we set the out_port to the OFPP_FLOOD, which is a flag to indicate that the packet should be sent to all ports.

		'''
		if dst in self.mac_to_port[dpid]:
			out_port = self.mac_to_port[dpid][dst]
		else:
			out_port = ofproto.OFPP_FLOOD

		# OFPActionOutput class is used with a packet_out message to specify a switch port that you want to send the packet out of.
		actions = [parser.OFPActionOutput(out_port)]

		# Install a fall to avoid packet-in next time - Means the packet does not come to the controller anymore, however, the switch can determine where to send the packet. 
		if out_port != ofproto.OFPP_FLOOD:
			match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
			self.add_flow(datapath, 1, match, actions)

		# Construct packet-out message.
		out = parser.OFPPacketOut(datapath = datapath, buffer_id = ofproto.OFP_NO_BUFFER, in_port = in_port, actions = actions, data = msg.data)

		datapath.send_msg(out)