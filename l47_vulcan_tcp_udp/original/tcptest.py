import os, sys, time
lib_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(lib_path)

from testutils.TestUtilsL47 import XenaScriptTools

class TCPTest(object):
    def __init__(self):
        self.classis_ip = os.environ.get('CHASSIS_IP_ADDR')
        self.classis_owner = os.environ.get('CHASSIS_OWNER')
        self.classis_pwd = os.environ.get('CHASSIS_PWD')
        self.classis_pe_num = os.environ.get('CHASSIS_PE_NUM')
        self.classis_ports_c = os.environ.get('CHASSIS_PORT_C')
        self.classis_ports_s = os.environ.get('CHASSIS_PORT_S')
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
        self.c_range = str(self.c_startip) + " " + str(self.c_conns) + str(" 100 1 9999999")
        self.s_range = str(self.s_startip) + str(" 1 5000 1")
        duration=0
        for dt in self.lp.split():
            duration = duration + int(dt)
        self.duration=duration
        self.ports_rx = self.classis_ports
        self.ports_tx = self.classis_ports

        self.rxpps_max = 0
        
    def setup(self):
        self.xm = XenaScriptTools(self.classis_ip)
        # self.xm.debug_on()
        # self.xm.halt_on()
        self.xm.logon_set_owner(self.classis_pwd, self.classis_owner)
        #self.xm.PortRelease(['1/6','1/7'])
        self.xm.port_reserve(self.classis_ports)
        time.sleep(3)
        self.xm.port_reset(self.classis_ports)
        time.sleep(3)
        self.xm.port_allocate_pe(self.classis_ports, self.classis_pe_num)



    def pre_test_all(self):
        self.xm.port_add_conn_group(self.classis_ports, self.cg_id, self.c_range, self.s_range, self.ip_ver)
        self.xm.port_role(self.classis_ports_c, self.cg_id, 'CLIENT')
        self.xm.port_role(self.classis_ports_s, self.cg_id, 'SERVER')

        for port in self.classis_ports:
            self.xm.send_expect_ok(port + " P4_SPEEDSELECTION {0}".format(self.speed))
            # Clear port counters
            self.xm.send_expect_ok(port + " P4_CLEAR_COUNTERS")

            # TCP scenario
            self.xm.send_expect_ok(port + " P4G_L4_PROTOCOL [{0}] TCP".format(self.cg_id))

            # Load profile
            self.xm.port_add_load_profile(port, self.cg_id, self.lp, "msec")
            self.xm.send_expect_ok(port + " P4G_IP_DS_TYPE [{0}] FIXED".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_IP_DS_VALUE [{0}] 0x00".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_L4_PROTOCOL [{0}] TCP".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_TCP_MSS_TYPE [{0}] FIXED".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_TCP_WINDOW_SIZE [{0}] 65535".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_TCP_WINDOW_SCALING [{0}] YES 3".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_TCP_DUP_THRES [{0}] 3".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_TCP_SYN_RTO [{0}] 3000 32 3".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_TCP_RTO [{0}] DYNAMIC 2000 32 3".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_TCP_CONGESTION_MODE [{0}] RENO".format(self.cg_id))
            ##use 100% speed
            self.xm.send_expect_ok(port + " P4G_RAW_UTILIZATION [{0}] 1000000".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_TX_DURING_RAMP [{0}] YES YES".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_L2_CLIENT_MAC [{0}] 0x00DEAD010101 DONT_EMBED_IP ".format(self.cg_id))

                
    def pre_test_64B(self):
        for port in self.classis_ports:
            self.xm.send_expect_ok(port + " P4G_RAW_CONN_INCARNATION [{0}] IMMORTAL".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_CLOSE_CONN [{0}] NONE".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_HAS_DOWNLOAD_REQ [{0}] YES".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_CONN_REPETITIONS [{0}] FINITE 300 ".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_REPEAT_LEN [{0}] 64".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_TOTAL_LEN [{0}] FINITE 64".format(self.cg_id))
            ####TCP protocol setup
            self.xm.send_expect_ok(port + " P4G_TCP_CONGESTION_MODE [{0}] NEW_RENO".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_TCP_WINDOW_SCALING [{0}] YES 3".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_TCP_WINDOW_SIZE [{0}] 65535".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_TCP_MSS_TYPE [{0}] FIXED".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_TCP_MSS_VALUE [{0}] 1460".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_TCP_DUP_THRES [{0}] 3".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_TCP_RTO [{0}] DYNAMIC 200 32 3".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_TCP_SYN_RTO [{0}] 2000 32 3".format(self.cg_id))
            ###  Raw mode , uoload
            self.xm.send_expect_ok(port + " P4G_TEST_APPLICATION [{0}] RAW".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_TEST_SCENARIO [{0}] DOWNLOAD".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_TYPE [{0}] FIXED".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_TOTAL_LEN [{0}] FINITE 64".format(self.cg_id))


    def pre_test_CC_1B(self):
        for port in self.classis_ports:
            self.xm.send_expect_ok(port + " P4G_TCP_MSS_VALUE [{0}] 1460".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_TEST_APPLICATION [{0}] RAW".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_TEST_SCENARIO [{0}] BOTH".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_TYPE [{0}] FIXED".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_TOTAL_LEN [{0}] FINITE 1".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD [{0}] 0 1 0x12".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_REPEAT_LEN [{0}] 1".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_HAS_DOWNLOAD_REQ [{0}] YES".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_DOWNLOAD_REQUEST [{0}] 1 0x42".format(self.cg_id))
            #self.xm.send_expect_ok(port + " P4G_RAW_REQUEST_REPEAT [{0}] FINITE 1".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_RX_PAYLOAD_LEN [{0}] FINITE 1".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_CONN_INCARNATION [{0}] IMMORTAL".format(self.cg_id))
            #P4G_RAW_CONN_LIFETIME should be the lp time add 
            ##############need modify  lp="5000 30000 35000 30000"
            print("{0}".format(self.duration))
            self.xm.send_expect_ok(port + " P4G_RAW_CONN_LIFETIME [{0}] MSEC {1}".format(self.cg_id, self.duration))
            self.xm.send_expect_ok(port + " P4G_RAW_CONN_REPETITIONS [{0}] INFINITE 0".format(self.cg_id))

    def pre_test_throughput_800B(self):
        for port in self.classis_ports:
            self.xm.send_expect_ok(port + " P4G_TCP_MSS_VALUE [{0}] 800".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_TEST_APPLICATION [{0}] RAW".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_TEST_SCENARIO [{0}] BOTH".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_TYPE [{0}] FIXED".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_TOTAL_LEN [{0}] INFINITE 99999999999".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD [{0}] 0 800 0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_REPEAT_LEN [{0}] 800".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_HAS_DOWNLOAD_REQ [{0}] YES".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_DOWNLOAD_REQUEST [{0}] 40 0x474554202f20485454502f312e310d0a486f73743a207777772e6d79686f73742e636f6d0d0a0d0a".format(self.cg_id))
            #self.xm.send_expect_ok(port + " P4G_RAW_REQUEST_REPEAT [{0}] FINITE 1".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_RX_PAYLOAD_LEN [{0}] INFINITE 4096".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_CONN_INCARNATION [{0}] IMMORTAL".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_CONN_LIFETIME [{0}] MSEC {1}".format(self.cg_id, self.duration))
            self.xm.send_expect_ok(port + " P4G_RAW_CONN_REPETITIONS [{0}] INFINITE 0".format(self.cg_id))

    def pre_test_throughput_1460B(self):
        for port in self.classis_ports:
            self.xm.send_expect_ok(port + " P4G_TCP_MSS_VALUE [{0}] 1460".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_TEST_APPLICATION [{0}] RAW".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_TEST_SCENARIO [{0}] BOTH".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_TYPE [{0}] INCREMENT".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_TOTAL_LEN [{0}] INFINITE 9999999999".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_REPEAT_LEN [{0}] 1460".format(self.cg_id))

            self.xm.send_expect_ok(port + " P4G_RAW_HAS_DOWNLOAD_REQ [{0}] YES".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_DOWNLOAD_REQUEST [{0}] 40 0x474554202f20485454502f312e310d0a486f73743a207777772e6d79686f73742e636f6d0d0a0d0a".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_RX_PAYLOAD_LEN [{0}] INFINITE 4096".format(self.cg_id))

            self.xm.send_expect_ok(port + " P4G_RAW_CONN_INCARNATION [{0}] IMMORTAL".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_CONN_LIFETIME [{0}] MSEC {1}".format(self.cg_id, self.duration))
            self.xm.send_expect_ok(port + " P4G_RAW_CONN_REPETITIONS [{0}] INFINITE 0".format(self.cg_id))
        

    def pre_test_cps_1B(self):
        for port in self.classis_ports:
            self.xm.send_expect_ok(port + " P4G_TCP_MSS_VALUE [{0}] 1460".format(self.cg_id))
            ###  Raw mode , uoload
            self.xm.send_expect_ok(port + " P4G_TEST_APPLICATION [{0}] RAW".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_TEST_SCENARIO [{0}] UPLOAD".format(self.cg_id))
            ### paylod setup ,download 1B ,upload 1B 
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_TYPE [{0}] FIXED".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_TOTAL_LEN [{0}] FINITE 1".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD [{0}] 0 1 0x12".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_REPEAT_LEN [{0}] 1".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_RX_PAYLOAD_LEN [{0}] FINITE 1".format(self.cg_id))
            ###IMMORTAL :after the connection lifetime,close the connection, and a new connection use a new port  
            self.xm.send_expect_ok(port + " P4G_RAW_CONN_INCARNATION [{0}] IMMORTAL".format(self.cg_id))
            ### one connection lifetime ,should close connection as soon as possible
            self.xm.send_expect_ok(port + " P4G_RAW_CONN_LIFETIME [{0}] MSECS 1".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_CONN_REPETITIONS [{0}] INFINITE 0".format(self.cg_id))


    def pre_test_cps_800B(self):
        for port in self.classis_ports:
            self.xm.send_expect_ok(port + " P4G_TCP_MSS_VALUE [{0}] 800".format(self.cg_id))
            ###  Raw mode , uoload
            self.xm.send_expect_ok(port + " P4G_TEST_APPLICATION [{0}] RAW".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_TEST_SCENARIO [{0}] UPLOAD".format(self.cg_id))
            ### paylod setup,upload 600B 
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_TYPE [{0}] FIXED".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_TOTAL_LEN [{0}] FINITE 800".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD [{0}] 0 800 0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_PAYLOAD_REPEAT_LEN [{0}] 800".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_RX_PAYLOAD_LEN [{0}] FINITE 800".format(self.cg_id))
            ###IMMORTAL :after the connection lifetime,close the connection, and a new connection use a new port  
            self.xm.send_expect_ok(port + " P4G_RAW_CONN_INCARNATION [{0}] IMMORTAL".format(self.cg_id))
            ### one connection lifetime ,should close connection as soon as possible
            self.xm.send_expect_ok(port + " P4G_RAW_CONN_LIFETIME [{0}] MSECS 1".format(self.cg_id))
            self.xm.send_expect_ok(port + " P4G_RAW_CONN_REPETITIONS [{0}] INFINITE 0".format(self.cg_id))


    def do_test_throughput(self):
        print("Traffic PREPARE")
        self.xm.port_prepare(self.classis_ports)
        self.xm.port_wait_state(self.classis_ports, "PREPARE_RDY")

        print("Traffic PRERUN")
        self.xm.port_set_traffic(self.classis_ports, "prerun")
        self.xm.port_wait_state(self.classis_ports, "PRERUN_RDY")

        print("Traffic ON (servers)")
        self.xm.port_set_traffic(self.classis_ports_s, "on")
        self.xm.port_wait_state(self.classis_ports_s, "RUNNING")

        print("Traffic ON (clients)")
        self.xm.port_set_traffic(self.classis_ports_c, "on")
        self.xm.port_wait_state(self.classis_ports_c, "RUNNING")

        waitsec = 2 + int(self.duration)/1000
        t0_milli = int(round(time.time() * 1000))
        rxbyte = 0
        txbyte = 0
        rxbps_max=0
        txbps_max=0
        while waitsec != 0:
            print("Waitsec: %d" % (waitsec))
            rxpps = 0
            for p in self.ports_rx:
                rx = self.xm.send(p + " P4_ETH_RX_COUNTERS ?").split()
                rxpps = rxpps + int(rx[5])

            if rxpps > self.rxpps_max:
                self.rxpps_max = rxpps

            time.sleep(1)
            waitsec-=1

        print("Traffic STOP")
        # self.xm.port_set_traffic(self.classis_ports, "stop")
        # self.xm.port_wait_state(self.classis_ports, "STOPPED")
        self.xm.port_state_off(self.classis_ports)

    def do_test_cps(self):
        print("Traffic PREPARE")
        self.xm.port_prepare(self.classis_ports)
        self.xm.port_wait_state(self.classis_ports, "PREPARE_RDY")

        print("Traffic PRERUN")
        self.xm.port_set_traffic(self.classis_ports, "prerun")
        self.xm.port_wait_state(self.classis_ports, "PRERUN_RDY")

        print("Traffic ON (servers)")
        self.xm.port_set_traffic(self.classis_ports_s, "on")
        self.xm.port_wait_state(self.classis_ports_s, "RUNNING")

        print("Traffic ON (clients)")
        self.xm.port_set_traffic(self.classis_ports_c, "on")
        self.xm.port_wait_state(self.classis_ports_c, "RUNNING")

        max_estab = 0
        min_estab = int(self.c_conns)/5
        wait_time = int(self.lp.split()[0])/1000
        up_time = int(self.lp.split()[1])/1000
        steady_time = int(self.lp.split()[2])/1000
        down_time = int(self.lp.split()[3])/1000

        time.sleep(wait_time+up_time)
        current_time=time.time()
        start_time = time.time()
        while current_time < start_time+steady_time :
            state=self.xm.send(self.classis_ports_c + " P4G_TCP_STATE_RATE [{0}] ?".format(self.cg_id))
            estab=int(state.split()[9])
            if estab > max_estab:
                    max_estab = estab
            if estab < min_estab and abs(estab-min_estab)/min_estab < 0.2 :
                    min_estab = estab
            time.sleep(1)  
            current_time=time.time()
        time.sleep(down_time)

        print("Traffic STOP")
        
        # self.xm.port_set_traffic(self.classis_ports, "stop")
        # self.xm.port_wait_state(self.classis_ports, "STOPPED")
        self.xm.port_state_off(self.classis_ports)
        fh_write = open('1.txt','w')
        fh_write.writelines([str(max_estab),' ',str(min_estab)])
        fh_write.close()


    def post_test_throughput(self):
        # dump port statistics
        self.xm.print_port_statistics(self.classis_ports)
        print("Getting TCP stats")
        est_conn=0
        for p in self.classis_ports:
            res = self.xm.send(p + " P4G_TCP_STATE_TOTAL [0] ?")
            est_conn = est_conn + int(res.split()[9])
        print("Requested conns: %d, established: %d" % (int(self.c_conns), est_conn/2))
        print("Max average Rx rate %d pps" % (self.rxpps_max))

    def post_test_cps(self):
    # dump port statistics
        self.xm.print_port_statistics(self.classis_ports)
        print("Getting TCP stats")
        est_conn=0
        for p in self.classis_ports:
            res = self.xm.send(p + " P4G_TCP_STATE_TOTAL [0] ?")
            est_conn = est_conn + int(res.split()[9])
        print("Requested conns: %d, established: %d" % (int(self.c_conns), est_conn/2))


    def cleanup(self):
        self.xm.port_set_free(self.classis_ports)
        self.xm.send_expect_ok("C_LOGOFF 1")


def tcpCC_1B():
    tcp_1B = TCPTest()
    tcp_1B.setup()
    tcp_1B.pre_test_all()
    tcp_1B.pre_test_CC_1B()
    tcp_1B.do_test_throughput()
    tcp_1B.post_test_throughput()
    tcp_1B.cleanup()

def tcpThroughput_800B():
    tcp_800B = TCPTest()
    tcp_800B.setup()
    tcp_800B.pre_test_all()
    tcp_800B.pre_test_throughput_800B()
    tcp_800B.do_test_throughput()
    tcp_800B.post_test_throughput()
    tcp_800B.cleanup()

def tcpThroughput_1460B():
    tcp_1460B = TCPTest()
    tcp_1460B.setup()
    tcp_1460B.pre_test_all()
    tcp_1460B.pre_test_throughput_1460B()
    tcp_1460B.do_test_throughput()
    tcp_1460B.post_test_throughput()
    tcp_1460B.cleanup()

def tcpCps_1B():
    tcp_1B = TCPTest()
    tcp_1B.setup()
    tcp_1B.pre_test_all()
    tcp_1B.pre_test_cps_1B()
    tcp_1B.do_test_cps()
    tcp_1B.post_test_cps()
    tcp_1B.cleanup()

def tcpCps_800B():
    tcp_1B = TCPTest()
    tcp_1B.setup()
    tcp_1B.pre_test_all()
    tcp_1B.pre_test_cps_800B()
    tcp_1B.do_test_cps()
    tcp_1B.post_test_cps()
    tcp_1B.cleanup()

def tcp_64B():
    tcp_64B = TCPTest()
    tcp_64B.setup()
    tcp_64B.pre_test_all()
    tcp_64B.pre_test_64B()
    tcp_64B.do_test_throughput()
    tcp_64B.post_test_throughput()
    tcp_64B.cleanup()
