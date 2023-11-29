#!/usr/bin/python
import os, sys, time, getopt, math


lib_path = os.path.abspath('testutils')
sys.path.append(lib_path)

from TestUtilsL47 import XenaScriptTools

class UDPTest(object):
    def __init__(self):
        self.classis_ip = os.environ.get('CLASSIS_IP_ADDR')
        self.classis_owner = os.environ.get('CLASSIS_OWNER')
        self.classis_pwd = os.environ.get('CLASSIS_PWD')
        self.classis_pe_num = os.environ.get('CLASSIS_PE_NUM')
        self.classis_ports_c = os.environ.get('CLASSIS_PORT_C')
        self.classis_ports_s = os.environ.get('CLASSIS_PORT_S')
        self.classis_ports = list()
        self.classis_ports.append(self.classis_ports_c)
        self.classis_ports.append(self.classis_ports_s)

        self.cg_id = os.environ.get('CG_ID')
        self.ip_ver = os.environ.get('IP_VER')
        self.lp = os.environ.get('LP')
        self.c_startip = os.environ.get('C_STARTIP')
        self.s_startip = os.environ.get('S_STARTIP')
        self.c_conns = os.environ.get('C_CONNS')
        self.speed = os.environ.get('SPEED')
        self.udp_type = os.environ.get('UDP_TYPE')
        self.udp_size = os.environ.get('UDP_SIZE')
        self.c_range = str(self.c_startip) +" " + str(self.c_conns) + str(" 100 1 9999999")
        self.s_range = str(self.s_startip) + str(" 1 5000 1")
        duration=0
        for dt in self.lp.split():
            duration = duration + int(dt)
        self.duration=duration
#        self.rxpps_max = 0

    def setup(self):
        self.xm = XenaScriptTools(self.classis_ip)
        self.xm.debugOn()
        self.xm.haltOn()
        self.xm.LogonSetOwner(self.classis_pwd, self.classis_owner)
        #self.xm.PortRelease(['1/6','1/7'])
        self.xm.PortReserve(self.classis_ports)
        time.sleep(3)
        self.xm.PortReset(self.classis_ports)
        time.sleep(3)
        self.xm.PortAllocatePE(self.classis_ports, self.classis_pe_num)
    

    def pre_test(self):
        self.xm.PortAddConnGroup(self.classis_ports, self.cg_id, self.c_range, self.s_range, self.ip_ver)
        self.xm.PortRole(self.classis_ports_c, self.cg_id, 'CLIENT')
        self.xm.PortRole(self.classis_ports_s, self.cg_id, 'SERVER')

        for port in self.classis_ports:
            self.xm.SendExpectOK(port + " P4_SPEEDSELECTION {0}".format(self.speed))
            # Clear port counters
            self.xm.SendExpectOK(port + " P4_CLEAR_COUNTERS")

            # UDP scenario
            self.xm.SendExpectOK(port + " P4G_L4_PROTOCOL [{0}] UDP".format(self.cg_id))

            # Load profile
            self.xm.PortAddLoadProfile(port, self.cg_id, self.lp, "msec")
    
            self.xm.SendExpectOK(port + " P4G_TEST_APPLICATION [{0}] RAW".format(self.cg_id))
            self.xm.SendExpectOK(port + " P4G_RAW_TEST_SCENARIO [{0}] BOTH".format(self.cg_id))
            
            # UDP packet size = fixed, 800 bytes (excl. ETH, IP, UDP headers) max = 1472
            self.xm.SendExpectOK(port + " P4G_UDP_PACKET_SIZE_TYPE [{0}] {1}".format(self.cg_id,self.udp_type))
            if self.udp_type == "FIXED":
                self.xm.SendExpectOK(port + " P4G_UDP_PACKET_SIZE_VALUE [{0}] {1}".format(self.cg_id,self.udp_size))
            else :
                self.xm.SendExpectOK(port + " P4G_UDP_PACKET_SIZE_MINMAX [{0}] 1 1472".format(self.cg_id))

            self.xm.SendExpectOK(port + " P4G_L2_CLIENT_MAC [{0}] 0x00DEAD010101 DONT_EMBED_IP ".format(self.cg_id))
            self.xm.SendExpectOK(port + " P4G_RAW_PAYLOAD_TYPE [{0}] INCREMENT".format(self.cg_id))
            self.xm.SendExpectOK(port + " P4G_RAW_PAYLOAD_TOTAL_LEN [{0}] INFINITE 0".format(self.cg_id))
            # Using 100% of the port speed.
            self.xm.SendExpectOK(port + " P4G_RAW_UTILIZATION [{0}] 1000000".format(self.cg_id))
            self.xm.SendExpectOK(port + " P4G_RAW_TX_DURING_RAMP [{0}] YES YES ".format(self.cg_id))
            # UDP streams live until the end of the test
            self.xm.SendExpectOK(port + " P4G_RAW_CONN_INCARNATION [{0}] ONCE".format(self.cg_id))

    def snat_pre_test(self):
        print("snat pre test begin")
        self.xm.SendExpectOK(self.classis_ports_c + " P4G_L2_CLIENT_MAC [{0}] 0x04F4A0000001 EMBED_IP".format(self.cg_id))
        self.xm.SendExpectOK(self.classis_ports_s + " P4G_L2_SERVER_MAC [{0}] 0x04F4A0000000 EMBED_IP".format(self.cg_id))
        self.xm.SendExpectOK(self.classis_ports_s + " P4G_L2_USE_ADDRESS_RES [{0}] YES".format(self.cg_id))
        self.xm.SendExpectOK(self.classis_ports_s + " P4G_L2_USE_GW [{0}] YES".format(self.cg_id))
        self.xm.SendExpectOK(self.classis_ports_s + " P4G_NAT [{0}] ON".format(self.cg_id))
        self.xm.SendExpectOK(self.classis_ports_s + " P4G_L2_GW [{0}] {1} 0x04F4A0000000".format(self.cg_id,self.s_startip))

    def dnat_pre_test(self):
        print("dnat pre test begin")
        self.xm.SendExpectOK(self.classis_ports_c + " P4G_SERVER_RANGE [{0}] 16.0.254.254 1 5000 1".format(self.cg_id))
        self.xm.SendExpectOK(self.classis_ports_c + " P4G_L2_CLIENT_MAC [{0}] 0x00DEAD020202 DONT_EMBED_IP".format(self.cg_id))
        self.xm.SendExpectOK(self.classis_ports_s + " P4G_L2_SERVER_MAC [{0}] 0x00DEAD010101 DONT_EMBED_IP".format(self.cg_id))
        for port in self.classis_ports:
            self.xm.SendExpectOK(port + " P4G_L2_USE_ADDRESS_RES [{0}] YES".format(self.cg_id))
            self.xm.SendExpectOK(port + " P4G_L2_USE_GW [{0}] YES".format(self.cg_id))

        self.xm.SendExpectOK(self.classis_ports_c + " P4G_L2_GW [{0}] 16.0.254.254 0x00DEAD010101".format(self.cg_id))
        self.xm.SendExpectOK(self.classis_ports_s + " P4G_L2_GW [{0}] 172.0.254.254 0x00DEAD020202".format(self.cg_id))

    def do_test(self):
        print("Traffic PREPARE")
        self.xm.PortPrepare(self.classis_ports)
        self.xm.PortWaitState(self.classis_ports, "PREPARE_RDY")

        print("Traffic PRERUN")
        self.xm.PortSetTraffic(self.classis_ports, "prerun")
        self.xm.PortWaitState(self.classis_ports, "PRERUN_RDY")

        print("Traffic ON (servers)")
        self.xm.PortSetTraffic(self.classis_ports_s, "on")
        self.xm.PortWaitState(self.classis_ports_s, "RUNNING")

        print("Traffic ON (clients)")
        self.xm.PortSetTraffic(self.classis_ports_c, "on")
        self.xm.PortWaitState(self.classis_ports_c, "RUNNING")

        waitsec = 2 + int(self.duration)/1000
        t0_milli = int(round(time.time() * 1000))
#        rxpps_max=0
        while waitsec != 0:
            print "Waitsec: %d" % (waitsec)
            rxpps = 0
            for p in self.classis_ports:
                rx = self.xm.Send(p + " P4_ETH_RX_COUNTERS ?").split()
#                rxpps = rxpps + int(rx[5])

#            if rxpps > self.rxpps_max:
#                self.rxpps_max = rxpps

            time.sleep(1)
            waitsec-=1

        print("Traffic STOP")
        self.xm.PortSetTraffic(self.classis_ports, "stop")
        self.xm.PortWaitState(self.classis_ports, "STOPPED")

    def post_test(self):
        # dump port statistics
        self.xm.PrintPortStatistics(self.classis_ports)
        est_conn=0
        pps_sum=0
        for p in self.classis_ports:
            res = self.xm.Send(p + " P4G_UDP_STATE_TOTAL [0] ?")
            est_conn = est_conn + int(res.split()[5])
            eth_res = self.xm.Send(p + " P4_ETH_RX_COUNTERS ?")
            pps_sum = pps_sum + int(eth_res.split()[7])
        pps = pps_sum/int(self.duration)*1000
        print "Requested conns: %d, established: %d" % (int(self.c_conns), est_conn/2)
        print("udp {0}/{1}B average Rx rate {2} pps".format(self.udp_type,self.udp_size,pps))

    def cleanup(self):
        self.xm.PortRelease(self.classis_ports)


def conntrack_udp_throughput():
    udpthroughput = UDPTest()
    udpthroughput.setup()
    udpthroughput.pre_test()
    udpthroughput.do_test()
    udpthroughput.post_test()
    udpthroughput.cleanup()

def conntrack_snat_throughput():
    udpthroughput = UDPTest()
    udpthroughput.setup()
    udpthroughput.pre_test()
    udpthroughput.snat_pre_test()
    udpthroughput.do_test()
    udpthroughput.post_test()
    udpthroughput.cleanup()


def conntrack_dnat_throughput():
    udpthroughput = UDPTest()
    udpthroughput.setup()
    udpthroughput.pre_test()
    udpthroughput.dnat_pre_test()
    udpthroughput.do_test()
    udpthroughput.post_test()
    udpthroughput.cleanup()
