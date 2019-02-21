import sys
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import packet_base
from ryu.lib.packet import tcp

count=0
class ExampleSwitch13(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ExampleSwitch13, self).__init__(*args, **kwargs)
        # initialize mac address table.
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        # install the table-miss flow entry.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        global count
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # get Datapath ID to identify OpenFlow switches.
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # analyse the received packets using the packet library.
        # printing out packet headers and datafield
        pkt = packet.Packet(msg.data)
        

                                #add packet to table of data
                                #add TCP UDP inspection
                                #number of packetsrecorded
                                #make them print every 5 
                                #packets to reduce overhead
        eth_pkt = pkt.get_protocol(ethernet.ethernet)

        dst = eth_pkt.dst
        src = eth_pkt.src
        
        # get the received port number from packet_in message.
        in_port = msg.match['in_port']
        
        if count==0:
            print "\t\t--------------------------------------\n" 
            sys.stdout.write('\t\tPacket Headers: ')
            print eth_pkt
            sys.stdout.flush()
            sys.stdout.write('\t\tData Field: ')
            print packet_base.PacketBase.parser(msg.data) #parses msg to get data
            sys.stdout.flush()
            sys.stdout.write('\t\tTCP Info: ')
            print tcp.tcp.parser(msg.data) #parses the msg to get TCP info
            sys.stdout.flush()
            sys.stdout.write('\t\tProtocols:\n')
            #displays protocols contained in packet
            for p in pkt.protocols:                          
                sys.stdout.write('\t\t\t')
                print p
                sys.stdout.flush()
        
            self.logger.info("\t\tDatapath ID: %s\n\t\tPort: %s", dpid, in_port)
            print "\n\t\t------------------------------------"
        if count==5:
            count=-1

        count+=1
        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        # if the destination mac address is already learned,
        # decide which port to output the packet, otherwise FLOOD.
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        # construct action list.
        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time.
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions)

        # construct packet_out message and send it.
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=in_port, actions=actions,
                                  data=msg.data)
        datapath.send_msg(out)

