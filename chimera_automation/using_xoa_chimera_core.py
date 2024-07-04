################################################################
#
#                   CHIMERA AUTOMATION
#
# The simple code example demonstrates how to automate Chimera 
# for network emulation:
# 
# 1. Change the module's media configuration
# 2. Configure Chimera port
# 3. Configure flow's basic filter on a port
# 4. Configure flow's extended filter on a port
# 5. Configure impairment - Drop
# 6. Configure impairment - Misordering
# 7. Configure impairment - Latency & Jitter
# 8. Configure impairment - Duplication
# 9. Configure impairment - Corruption
# 10. Configure bandwidth control - Policer
# 11. Configure bandwidth control - Shaper
# 12. Flow statistics
# 13. Port statistics
#
################################################################

import asyncio
from ipaddress import IPv4Address, IPv6Address
import logging

from chimera_core.controller import MainController
from chimera_core.types import distributions, enums, dataset

#---------------------------
# GLOBAL PARAMS
#---------------------------
CHASSIS_IP = "87.61.110.118"
USERNAME = "XOA"
PORT = "2/0"
FLOW_IDX = 1

async def chimera_using_chimera_core_func(chassis: str, username: str, port_str: str, flow_id: int) -> None:

    # configure basic logger
    logging.basicConfig(
        format="%(asctime)s  %(message)s",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(filename="test.log", mode="a"),
            logging.StreamHandler()]
        )

    # create credential object
    credentials = dataset.Credentials(
        product=dataset.EProductType.VALKYRIE,
        host=chassis)
    
    #----------------------------------------------
    # 1. Connect to Valkyrie chassis and select port
    # ---------------------------------------------
    # region Connect to Valkyrie chassis and select port

    # create chimera core controller object
    controller = await MainController()

    # add chimera emulator into the chassis inventory and get the ID
    tester_id = await controller.add_tester(credentials=credentials)

    # create tester object
    tester = await controller.use_tester(tester_id, username=username, reserve=False, debug=False)

    # create module object
    _mid = int(port_str.split("/")[0])
    _pid = int(port_str.split("/")[1])
    module_obj = await tester.use_module(module_id=_mid, reserve=False)

    # free the module in case it is reserved by others
    await module_obj.free(should_free_sub_resources=True)
    await module_obj.reserve()

    # create port object and reserver the port
    port_obj = await tester.use_port(module_id=_mid, port_id=_pid, reserve=False)

    # reserve the port
    await port_obj.reserve()

    # reset port
    await port_obj.reset()

    # endregion

    #----------------------------------------------
    # 2. Configure Chimera port
    # ---------------------------------------------
    # region Configure Chimera port
    port_config = await port_obj.config.get()
    port_config.comment = "My Chimera Port"

    port_config.set_fcs_error_mode_discard()
    port_config.set_fcs_error_mode_pass()

    port_config.set_link_flap(enable=enums.OnOff.ON, duration=100, period=1000, repetition=0)
    port_config.set_link_flap_off()

    port_config.set_pma_error_pulse(enable=enums.OnOff.ON, duration=100, period=1000, repetition=0, coeff=100, exp=-4)
    port_config.set_pma_error_pulse_off()

    port_config.set_impairment_off()
    port_config.set_impairment_on()

    port_config.tpld_mode = enums.TPLDMode.NORMAL
    port_config.tpld_mode = enums.TPLDMode.MICRO

    await port_obj.config.set(port_config)

    # endregion

    #----------------------------------------------
    # 3. Configure flow's basic filter on a port
    # ---------------------------------------------
    # region Flow configuration + basic filter on a port

    # Configure flow properties
    flow = port_obj.flows[flow_id]
    flow_config = await flow.get()
    flow_config.comment = "Flow description"
    await flow.set(config=flow_config)

    # Initialize shadow filter on the flow
    shadow_filter = flow.shadow_filter
    await shadow_filter.init()
    await shadow_filter.clear()
    
    # Configure shadow filter to BASIC mode
    basic_filter = await shadow_filter.use_basic_mode()
    basic_filter_config = await basic_filter.get()

    await basic_filter.set(basic_filter_config)
    await shadow_filter.enable()
    await shadow_filter.apply()


    #------------------
    # Ethernet subfilter
    #------------------
    # Use and configure basic-mode shadow filter's Ethernet subfilter
    ethernet_subfilter = basic_filter_config.layer_2.use_ethernet()
    ethernet_subfilter.exclude()
    ethernet_subfilter.include()
    ethernet_subfilter.src_addr.on(value=dataset.Hex("AAAAAAAAAAAA"), mask=dataset.Hex("FFFFFFFFFFFF"))
    ethernet_subfilter.dest_addr.on(value=dataset.Hex("BBBBBBBBBBBB"), mask=dataset.Hex("FFFFFFFFFFFF"))

    #------------------
    # Layer 2+ subfilter
    #------------------
    # Not use basic-mode shadow filter's Layer 2+ subfilter
    layer_2_plus_subfilter = basic_filter_config.layer_2_plus.use_none()

    # Use and configure basic-mode shadow filter's Layer2+ subfilter (One VLAN tag)
    layer_2_plus_subfilter = basic_filter_config.layer_2_plus.use_1_vlan_tag()
    layer_2_plus_subfilter.off()
    layer_2_plus_subfilter.exclude()
    layer_2_plus_subfilter.include()
    layer_2_plus_subfilter.tag_inner.on(value=1234, mask=dataset.Hex("FFF"))
    layer_2_plus_subfilter.pcp_inner.on(value=3, mask=dataset.Hex("7"))

    # Use and configure basic-mode shadow filter's Layer2+ subfilter (Two VLAN tag)
    layer_2_plus_subfilter = basic_filter_config.layer_2_plus.use_2_vlan_tags()
    layer_2_plus_subfilter.off()
    layer_2_plus_subfilter.exclude()
    layer_2_plus_subfilter.include()
    layer_2_plus_subfilter.tag_inner.on(value=1234, mask=dataset.Hex("FFF"))
    layer_2_plus_subfilter.pcp_inner.on(value=3, mask=dataset.Hex("7"))
    layer_2_plus_subfilter.tag_outer.on(value=2345, mask=dataset.Hex("FFF"))
    layer_2_plus_subfilter.pcp_outer.on(value=0, mask=dataset.Hex("7"))

    # Use and configure basic-mode shadow filter's Layer2+ subfilter (MPLS)
    layer_2_plus_subfilter = basic_filter_config.layer_2_plus.use_mpls()
    layer_2_plus_subfilter.off()
    layer_2_plus_subfilter.exclude()
    layer_2_plus_subfilter.include()
    layer_2_plus_subfilter.label.on(value=1000, mask=dataset.Hex("FFFFF"))
    layer_2_plus_subfilter.toc.on(value=0, mask=dataset.Hex("7"))


    #------------------
    # Layer 3 subfilter
    #------------------
    # Not use basic-mode shadow filter's Layer 3 subfilter
    layer_3_subfilter = basic_filter_config.layer_3.use_none()
    
    # Use and configure basic-mode shadow filter's Layer 3 subfilter (IPv4)
    layer_3_subfilter = basic_filter_config.layer_3.use_ipv4()
    layer_3_subfilter.off()
    layer_3_subfilter.exclude()
    layer_3_subfilter.include()
    layer_3_subfilter.src_addr.on(value=IPv4Address("10.0.0.2"), mask=dataset.Hex("FFFFFFFF"))
    layer_3_subfilter.dest_addr.on(value=IPv4Address("11.0.0.2"), mask=dataset.Hex("FFFFFFFF"))
    layer_3_subfilter.dscp.on(value=0, mask=dataset.Hex("FC"))

    # Use and configure basic-mode shadow filter's Layer 3 subfilter (IPv6)
    layer_3_subfilter = basic_filter_config.layer_3.use_ipv6()
    layer_3_subfilter.exclude()
    layer_3_subfilter.include()
    layer_3_subfilter.src_addr.on(value=IPv6Address("2001::2"), mask=dataset.Hex("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"))
    layer_3_subfilter.dest_addr.on(value=IPv6Address("2002::2"), mask=dataset.Hex("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"))
    layer_3_subfilter.tc.on(value=0, mask=dataset.Hex("FC"))


    #------------------
    # Layer 4 subfilter
    #------------------
    # Not use basic-mode shadow filter's Layer 4 subfilter
    layer_4_subfilter = basic_filter_config.layer_4.use_none()
    
    # Use and configure basic-mode shadow filter's Layer 4 subfilter (TCP)
    layer_4_subfilter = basic_filter_config.layer_4.use_tcp()
    layer_4_subfilter.off()
    layer_4_subfilter.exclude()
    layer_4_subfilter.include()
    layer_4_subfilter.src_port.on(value=1234, mask=dataset.Hex("FFFF"))
    layer_4_subfilter.dest_port.on(value=80, mask=dataset.Hex("FFFF"))

    # Use and configure basic-mode shadow filter's Layer 4 subfilter (UDP)
    layer_4_subfilter = basic_filter_config.layer_4.use_udp()
    layer_4_subfilter.off()
    layer_4_subfilter.exclude()
    layer_4_subfilter.include()
    layer_4_subfilter.src_port.on(value=1234, mask=dataset.Hex("FFFF"))
    layer_4_subfilter.dest_port.on(value=80, mask=dataset.Hex("FFFF"))


    #------------------
    # Layer Xena subfilter
    #------------------
    # Not use basic-mode shadow filter's Layer Xena subfilter
    layer_xena_subfilter = basic_filter_config.layer_xena.use_none()

    # Use and configure basic-mode shadow filter's TPLD subfilter
    layer_xena_subfilter = basic_filter_config.layer_xena.use_tpld()
    layer_xena_subfilter.exclude()
    layer_xena_subfilter.include()
    layer_xena_subfilter[0].on(tpld_id=2)       
    layer_xena_subfilter[0].off()
    layer_xena_subfilter[1].on(tpld_id=4)       
    layer_xena_subfilter[1].off()
    layer_xena_subfilter[2].on(tpld_id=6)       
    layer_xena_subfilter[2].off()
    layer_xena_subfilter[3].on(tpld_id=8)       
    layer_xena_subfilter[3].off()
    layer_xena_subfilter[4].on(tpld_id=10)       
    layer_xena_subfilter[4].off()
    layer_xena_subfilter[5].on(tpld_id=20)       
    layer_xena_subfilter[5].off()
    layer_xena_subfilter[6].on(tpld_id=40)       
    layer_xena_subfilter[6].off()
    layer_xena_subfilter[7].on(tpld_id=60)       
    layer_xena_subfilter[7].off()
    layer_xena_subfilter[8].on(tpld_id=80)       
    layer_xena_subfilter[8].off()
    layer_xena_subfilter[9].on(tpld_id=100)       
    layer_xena_subfilter[9].off()
    layer_xena_subfilter[10].on(tpld_id=102)       
    layer_xena_subfilter[10].off()
    layer_xena_subfilter[11].on(tpld_id=104)       
    layer_xena_subfilter[11].off()
    layer_xena_subfilter[12].on(tpld_id=106)       
    layer_xena_subfilter[12].off()
    layer_xena_subfilter[13].on(tpld_id=108)       
    layer_xena_subfilter[13].off()
    layer_xena_subfilter[14].on(tpld_id=110)       
    layer_xena_subfilter[14].off()
    layer_xena_subfilter[15].on(tpld_id=200)       
    layer_xena_subfilter[15].off()

    #------------------
    # Layer Any subfilter
    #------------------
    # Not use basic-mode shadow filter's Layer Any subfilter
    layer_any_subfilter = basic_filter_config.layer_any.use_none()

    # Use and configure basic-mode shadow filter's Layer 4 subfilter (TCP)
    layer_any_subfilter = basic_filter_config.layer_any.use_any_field()
    layer_any_subfilter.off()
    layer_any_subfilter.exclude()
    layer_any_subfilter.include()
    layer_any_subfilter.on(position=0, value=dataset.Hex("112233445566"), mask=dataset.Hex("112233445566"))


    # Enable and apply the basic filter settings
    await basic_filter.set(basic_filter_config)
    await shadow_filter.enable()
    await shadow_filter.apply()

    # endregion

    #----------------------------------------------
    # 4. Configure flow's extended filter on a port
    # ---------------------------------------------
    # region Flow configuration + extended filter on a port

    # Configure flow properties
    flow = port_obj.flows[flow_id]
    flow_config = await flow.get()
    flow_config.comment = "Flow description"
    await flow.set(config=flow_config)

    # Initialize shadow filter on the flow
    shadow_filter = flow.shadow_filter
    await shadow_filter.init()
    await shadow_filter.clear()

    # Configure shadow filter to EXTENDED mode
    extended_filter = await shadow_filter.use_extended_mode()
    extended_filter_config = await extended_filter.get()

    ethernet = dataset.ProtocolSegement(
        protocol_type=dataset.ProtocolOption.ETHERNET,
        value='00001111',
        mask='11110000',
    )
    ipv4_1 = dataset.ProtocolSegement(
        protocol_type=dataset.ProtocolOption.IP,
        value='00001111',
        mask='11110000',
    )
    ipv4_2 = dataset.ProtocolSegement(
        protocol_type=dataset.ProtocolOption.IP,
        value='00001111',
        mask='11110000',
    )
    extended_filter_config.protocol_segments = (ethernet, ipv4_1, ipv4_2)

    await extended_filter.set(extended_filter_config)
    await shadow_filter.enable()
    await shadow_filter.apply()

    # endregion

    #----------------------------------------------
    # 5. Configure impairment - Drop
    # ---------------------------------------------
    # region Configure impairment - Drop

    # Fixed Burst distribution for impairment Drop
    dist = distributions.drop.FixedBurst(burst_size=5)
    dist.repeat(period=5)
    dist.one_shot()

    # Random Burst distribution for impairment Drop
    dist = distributions.drop.RandomBurst(minimum=1, maximum=10, probability=10_000)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Fixed Rate distribution for impairment Drop
    dist = distributions.drop.FixedRate(probability=10_000)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Bit Error Rate distribution for impairment Drop
    dist = distributions.drop.BitErrorRate(coefficient=1, exponent=1)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Random Rate distribution for impairment Drop
    dist = distributions.drop.RandomRate(probability=10_000)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Gilbert Elliot distribution for impairment Drop
    dist = distributions.drop.GilbertElliot(good_state_impair_prob=0, good_state_trans_prob=0, bad_state_impair_prob=0, bad_state_trans_prob=0)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Uniform distribution for impairment Drop
    dist = distributions.drop.Uniform(minimum=1, maximum=1)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Gaussian distribution for impairment Drop
    dist = distributions.drop.Gaussian(mean=1, sd=1)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Poisson distribution for impairment Drop
    dist = distributions.drop.Poisson(lamda=9)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Gamma distribution for impairment Drop
    dist = distributions.drop.Gamma(shape=1, scale=1)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Custom distribution for impairment Drop
    data_x=[0, 1] * 256
    custom_distribution = await port_obj.custom_distributions.add(
        linear=False,
        entry_count = len(data_x),
        data_x=data_x,
        comment="Example Custom Distribution"
    )
    dist = distributions.drop.Custom(custom_distribution=custom_distribution)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Set distribution and start impairment Drop
    drop_config = await flow.drop.get()
    drop_config.set_distribution(dist)
    await flow.drop.start(drop_config)
    await flow.drop.stop(drop_config)

    # endregion

    #----------------------------------------------
    # 6. Configure impairment - Misordering
    # ---------------------------------------------
    # region Configure impairment - Misordering

    # Fixed Burst distribution for impairment Misordering
    dist = distributions.misordering.FixedBurst(burst_size=1)
    dist.repeat(period=5)
    dist.one_shot()

    # Fixed Rate distribution for impairment Misordering
    dist = distributions.misordering.FixedRate(probability=10_000)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Set distribution and start impairment Misordering
    misordering_config = await flow.misordering.get()
    misordering_config.depth = 1
    misordering_config.set_distribution(dist)
    await flow.misordering.start(misordering_config)
    await flow.misordering.stop(misordering_config)

    # endregion

    #----------------------------------------------
    # 7. Configure impairment - Latency & Jitter
    # ---------------------------------------------
    # region Configure impairment - Latency & Jitter

    # Fixed Burst distribution for impairment Latency & Jitter
    dist = distributions.latency_jitter.ConstantDelay(delay=100)


    # Random Burst distribution for impairment Latency & Jitter
    dist = distributions.latency_jitter.AccumulateBurst(burst_delay=1300)
    dist.repeat(period=1)
    dist.one_shot()

    # Step distribution for impairment Latency & Jitter
    dist = distributions.latency_jitter.Step(min=1300, max=77000)
    dist.continuous()

    # Uniform distribution for impairment Latency & Jitter
    dist = distributions.latency_jitter.Uniform(minimum=1, maximum=1)
    dist.continuous()

    # Gaussian distribution for impairment Latency & Jitter
    dist = distributions.latency_jitter.Gaussian(mean=1, sd=1)
    dist.continuous()

    # Poisson distribution for impairment Latency & Jitter
    dist = distributions.latency_jitter.Poisson(lamda=9)
    dist.continuous()

    # Gamma distribution for impairment Latency & Jitter
    dist = distributions.latency_jitter.Gamma(shape=1, scale=1)
    dist.continuous()

    # Custom distribution for impairment Latency & Jitter
    data_x=[0, 1] * 256
    custom_distribution = await port_obj.custom_distributions.add(
        linear=False,
        entry_count = len(data_x),
        data_x=data_x,
        comment="Example Custom Distribution"
    )
    dist = distributions.latency_jitter.Custom(custom_distribution=custom_distribution)
    dist.continuous()

    # Set distribution and start impairment Latency & Jitter
    latency_jitter_config = await flow.latency_jitter.get()
    latency_jitter_config.set_distribution(dist)
    await flow.latency_jitter.start(latency_jitter_config)
    await flow.latency_jitter.stop(latency_jitter_config)

    # endregion

    #----------------------------------------------
    # 8. Configure impairment - Duplication
    # ---------------------------------------------
    # region Configure impairment - Duplication

    # Fixed Burst distribution for impairment Duplication
    dist = distributions.duplication.FixedBurst(burst_size=5)
    dist.repeat(period=5)
    dist.one_shot()

    # Random Burst distribution for impairment Duplication
    dist = distributions.duplication.RandomBurst(minimum=1, maximum=10, probability=10_000)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Fixed Rate distribution for impairment Duplication
    dist = distributions.duplication.FixedRate(probability=10_000)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Bit Error Rate distribution for impairment Duplication
    dist = distributions.duplication.BitErrorRate(coefficient=1, exponent=1)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Random Rate distribution for impairment Duplication
    dist = distributions.duplication.RandomRate(probability=10_000)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Gilbert Elliot distribution for impairment Duplication
    dist = distributions.duplication.GilbertElliot(good_state_impair_prob=0, good_state_trans_prob=0, bad_state_impair_prob=0, bad_state_trans_prob=0)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Uniform distribution for impairment Duplication
    dist = distributions.duplication.Uniform(minimum=1, maximum=1)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Gaussian distribution for impairment Duplication
    dist = distributions.duplication.Gaussian(mean=1, sd=1)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Poisson distribution for impairment Duplication
    dist = distributions.duplication.Poisson(lamda=9)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Gamma distribution for impairment Duplication
    dist = distributions.duplication.Gamma(shape=1, scale=1)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Custom distribution for impairment Duplication
    data_x=[0, 1] * 256
    custom_distribution = await port_obj.custom_distributions.add(
        linear=False,
        entry_count = len(data_x),
        data_x=data_x,
        comment="Example Custom Distribution"
    )
    dist = distributions.duplication.Custom(custom_distribution=custom_distribution)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Set distribution and start impairment Duplication
    duplication_config = await flow.duplication.get()
    duplication_config.set_distribution(dist)
    await flow.duplication.start(duplication_config)
    await flow.duplication.stop(duplication_config)

    # endregion

    #----------------------------------------------
    # 9. Configure impairment - Corruption
    # ---------------------------------------------
    # region Configure impairment - Corruption

    # Fixed Burst distribution for impairment Corruption
    dist = distributions.corruption.FixedBurst(burst_size=5)
    dist.repeat(period=5)
    dist.one_shot()

    # Random Burst distribution for impairment Corruption
    dist = distributions.corruption.RandomBurst(minimum=1, maximum=10, probability=10_000)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Fixed Rate distribution for impairment Corruption
    dist = distributions.corruption.FixedRate(probability=10_000)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Bit Error Rate distribution for impairment Corruption
    dist = distributions.corruption.BitErrorRate(coefficient=1, exponent=1)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Random Rate distribution for impairment Corruption
    dist = distributions.corruption.RandomRate(probability=10_000)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Gilbert Elliot distribution for impairment Corruption
    dist = distributions.corruption.GilbertElliot(good_state_impair_prob=0, good_state_trans_prob=0, bad_state_impair_prob=0, bad_state_trans_prob=0)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Uniform distribution for impairment Corruption
    dist = distributions.corruption.Uniform(minimum=1, maximum=1)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Gaussian distribution for impairment Corruption
    dist = distributions.corruption.Gaussian(mean=1, sd=1)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Poisson distribution for impairment Corruption
    dist = distributions.corruption.Poisson(lamda=9)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Gamma distribution for impairment Corruption
    dist = distributions.corruption.Gamma(shape=1, scale=1)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Custom distribution for impairment Corruption
    data_x=[0, 1] * 256
    custom_distribution = await port_obj.custom_distributions.add(
        linear=False,
        entry_count = len(data_x),
        data_x=data_x,
        comment="Example Custom Distribution"
    )
    dist = distributions.corruption.Custom(custom_distribution=custom_distribution)
    dist.repeat_pattern(duration=1, period=1)
    dist.continuous()

    # Set distribution and start impairment Corruption
    corruption_config = await flow.corruption.get()
    corruption_config.corruption_type = enums.CorruptionType.ETH
    corruption_config.corruption_type = enums.CorruptionType.IP
    corruption_config.corruption_type = enums.CorruptionType.TCP
    corruption_config.corruption_type = enums.CorruptionType.UDP
    corruption_config.corruption_type = enums.CorruptionType.BER
    corruption_config.set_distribution(dist)
    await flow.corruption.start(corruption_config)
    await flow.corruption.stop(corruption_config)

    # endregion

    #----------------------------------------------
    # 10. Configure bandwidth control - Policer
    # ---------------------------------------------
    # region Configure bandwidth control - Policer

    # Set and start bandwidth control Policer
    policer_config = await flow.policer.get()
    policer_config.set_control_mode(mode=enums.PolicerMode.L1)
    policer_config.set_control_on_l1()
    policer_config.set_control_mode(mode=enums.PolicerMode.L2)
    policer_config.set_control_on_l2()
    policer_config.mode = enums.PolicerMode.L1
    policer_config.mode = enums.PolicerMode.L2
    policer_config.cir = 10_000
    policer_config.cbs = 1_000
    policer_config.set_on_off(on_off=enums.OnOff.ON)
    policer_config.set_on()
    policer_config.set_on_off(on_off=enums.OnOff.OFF)
    policer_config.set_off()
    await flow.policer.start(policer_config)
    await flow.policer.stop(policer_config)

    # endregion

    #----------------------------------------------
    # 11. Configure bandwidth control - Shaper
    # ---------------------------------------------
    # region Configure bandwidth control - Shaper

    # Set and start bandwidth control Shaper
    shaper_config = await flow.shaper.get()
    shaper_config.set_control_mode(mode=enums.PolicerMode.L1)
    shaper_config.set_control_on_l1()
    shaper_config.set_control_mode(mode=enums.PolicerMode.L2)
    shaper_config.set_control_on_l2()
    shaper_config.mode = enums.PolicerMode.L1
    shaper_config.mode = enums.PolicerMode.L2
    shaper_config.cir = 10_000
    shaper_config.cbs = 1_000
    shaper_config.buffer_size = 1_000
    shaper_config.set_on_off(on_off=enums.OnOff.ON)
    shaper_config.set_on()
    shaper_config.set_on_off(on_off=enums.OnOff.OFF)
    shaper_config.set_off()
    await flow.shaper.start(shaper_config)
    await flow.shaper.stop(shaper_config)

    # endregion

    #----------------------------------------------
    # 12. Flow statistics
    # ---------------------------------------------
    # region Flow Statistics

    rx_total = await flow.statistics.rx.total.get()
    rx_total.byte_count
    rx_total.packet_count
    rx_total.l2_bps
    rx_total.pps

    tx_total = await flow.statistics.tx.total.get()
    tx_total.byte_count
    tx_total.packet_count
    tx_total.l2_bps
    tx_total.pps

    flow_drop_total = await flow.statistics.total.dropped.get()
    flow_drop_total.pkt_drop_count_total
    flow_drop_total.pkt_drop_count_programmed
    flow_drop_total.pkt_drop_count_bandwidth
    flow_drop_total.pkt_drop_count_other
    flow_drop_total.pkt_drop_ratio_total
    flow_drop_total.pkt_drop_ratio_programmed
    flow_drop_total.pkt_drop_ratio_bandwidth
    flow_drop_total.pkt_drop_ratio_other

    flow_corrupted_total = await flow.statistics.total.corrupted.get()
    flow_corrupted_total.fcs_corrupted_pkt_count
    flow_corrupted_total.fcs_corrupted_pkt_ratio
    flow_corrupted_total.ip_corrupted_pkt_count
    flow_corrupted_total.ip_corrupted_pkt_ratio
    flow_corrupted_total.tcp_corrupted_pkt_count
    flow_corrupted_total.tcp_corrupted_pkt_ratio
    flow_corrupted_total.total_corrupted_pkt_count
    flow_corrupted_total.total_corrupted_pkt_ratio
    flow_corrupted_total.udp_corrupted_pkt_count
    flow_corrupted_total.udp_corrupted_pkt_ratio

    flow_delayed_total = await flow.statistics.total.delayed.get()
    flow_delayed_total.pkt_count
    flow_delayed_total.ratio

    flow_jittered_total = await flow.statistics.total.jittered.get()
    flow_jittered_total.pkt_count
    flow_jittered_total.ratio

    flow_duplicated_total = await flow.statistics.total.duplicated.get()
    flow_duplicated_total.pkt_count
    flow_duplicated_total.ratio

    flow_misordered_total = await flow.statistics.total.misordered.get()
    flow_misordered_total.pkt_count
    flow_misordered_total.ratio

    await flow.statistics.tx.clear.set()
    await flow.statistics.rx.clear.set()
    await flow.statistics.clear.set()
    
    # endregion

    #----------------------------------------------
    # 13. Port statistics
    # ---------------------------------------------
    # region Port Statistics
    port_drop = await port_obj.config.statistics.dropped.get()
    port_drop.pkt_drop_count_total
    port_drop.pkt_drop_count_programmed
    port_drop.pkt_drop_count_bandwidth
    port_drop.pkt_drop_count_other
    port_drop.pkt_drop_ratio_total
    port_drop.pkt_drop_ratio_programmed
    port_drop.pkt_drop_ratio_bandwidth
    port_drop.pkt_drop_ratio_other

    port_corrupted = await port_obj.config.statistics.corrupted.get()
    port_corrupted.fcs_corrupted_pkt_count
    port_corrupted.fcs_corrupted_pkt_ratio
    port_corrupted.ip_corrupted_pkt_count
    port_corrupted.ip_corrupted_pkt_ratio
    port_corrupted.tcp_corrupted_pkt_count
    port_corrupted.tcp_corrupted_pkt_ratio
    port_corrupted.total_corrupted_pkt_count
    port_corrupted.total_corrupted_pkt_ratio
    port_corrupted.udp_corrupted_pkt_count
    port_corrupted.udp_corrupted_pkt_ratio

    port_delayed = await port_obj.config.statistics.delayed.get()
    port_delayed.pkt_count
    port_delayed.ratio

    port_jittered = await port_obj.config.statistics.jittered.get()
    port_jittered.pkt_count
    port_jittered.ratio

    port_duplicated = await port_obj.config.statistics.duplicated.get()
    port_duplicated.pkt_count
    port_duplicated.ratio

    port_misordered = await port_obj.config.statistics.misordered.get()
    port_misordered.pkt_count
    port_misordered.ratio

    await port_obj.config.statistics.clear.set()

    # endregion

async def main() -> None:
    stop_event = asyncio.Event()
    await chimera_using_chimera_core_func(
        chassis=CHASSIS_IP, 
        username=USERNAME,
        port_str=PORT,
        flow_id=FLOW_IDX
        )

if __name__ == "__main__":
    asyncio.run(main())