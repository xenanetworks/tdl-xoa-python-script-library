# XOA Script Documentation - Filter traffic statistics

## Introduction
What this script example does:
1. Connect to a tester
2. Reserve a port for TX and another one for RX
3. Create a simple stream on TX port with 100% rate
4. Create a filter on RX port
5. Start traffic on TX port
6. Read RX and TX L2 traffic statistics
7. Calculate L1 traffic rate based on L2 statistics
8. Stop traffic

As to traffic rate statistics, you can only get L2 statistics from the commands, including bits per second (bps) and frames per second (fps). Use the following equation to calculate L1 bits per second.

* On TX side: ``l1_bit_per_sec = l2_fps * (interframe_gap + frame_size) * 8``
* On RX side: ``l1_bit_per_sec = l2_fps * interframe_gap * 8 + l2_bit_per_sec``

> Note: The **inter-frame gap on both TX and RX sides must be the same**, otherwise the calculated L1 bps values will be different.