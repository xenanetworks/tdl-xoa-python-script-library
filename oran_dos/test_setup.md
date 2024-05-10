# 1. Introduction
Due to the open and disaggregated nature of the O-RAN system (SUT), the attack surfaces associated with some of its critical transport protocols and major interfaces of the O-RAN system become easy targets for potential attackers. Cyber attacks like DoS, fuzzing and blind exploitation types are easy to launch, require little information on the target system, and could cause significant performance degradation, or even the service interruption if not properly mitigated.

This file describes how to do the Dos and Fuzzing Tests with Xena test platform.

# 2. Test setup and configuration
## 2.1 S-Plane PTP DoS Attack
### 2.1.1 Test Description
The purpose of the test is to verify that a predefined volumetric DoS attack against O-DU S-Plane will not degrade service availability or performance of the SUT in a meaningful way.

### 2.1.2 Test setup and configuration
The test requires easy to access MAC address information of the O-DU’s open fronthaul interface and L2 connectivity (e.g. over L2 network switching device) to the target from the emulated attacker.

### 2.1.3 Test procedure
 
* Ensure normal UE procedures1 and user-plane traffic can be handled properly through the SUT. It is recommended to use Section 5.6 Bidirectional throughput in different radio conditions and Section 6.1 Data Services tests as a benchmark for indicating correct behavior of the SUT.

* Use test tool to generate various level of volumetric DoS attack against the MAC address of the O-DU S-Plane
  * Volumetric tiers: 10Mbps, 100Mbps, 1Gbps
  * DoS Traffic types: generic Ethernet frames, PTP announce/sync message
  * DoS source address: spoofed MAC of PTPGM, random source MACs
  * Observe the functional and performance impact of the SUT

### 2.1.5	Expected Results

* No meaningful degradation of service availability and performance of the SUT. It is recommended to use Sec. 5.6 Bidirectional throughput in different radio conditions and Section 6.1 Data Services tests as a benchmark for indicating correct behavior of the SUT.
* DoS attacks should be mitigated by O-DU

## 2.2 C-Plan eCPRI DoS Attack
## # 2.2.1 Test Description
The purpose of the test is to verify that a predefined volumetric DoS attack against O-DU C-Plane will not degrade service availability or performance of the SUT in a meaningful way.

### 2.2.2	Test setup and configuration
The test requires easy to access MAC address information of the O-DU’s open fronthaul interface and L2 connectivity (e.g. over L2 network switching device) to the target from the emulated attacker.

### 2.2.3 Test procedure

* Ensure normal UE procedures1 and user-plane traffic can be handled properly through the SUT. It is recommended to use Section 5.6 Bidirectional throughput in different radio conditions and Section 6.1 Data Services tests as a benchmark for indicating correct behavior of the SUT.
* Use test tool to generate various level of volumetric DoS attack against the MAC address of the O-DU C-Plane
 * Volumetric tiers: 10Mbps, 100Mbps, 1Gbps
 * DoS Traffic types: eCPRI real-time ctrl data message over Ethernet
 * DoS source address: spoofed MAC of O-RU(s), random source MACs
* Observe the functional and performance impact of the SUT.

### 2.2.4 Expected Results

* No meaningful degradation of service availability and performance of the SUT. It is recommended to use Sec. 5.6 Bidirectional throughput in different radio conditions and Section 6.1 Data Services tests as a benchmark for indicating correct behavior of the SUT.
* DoS attacks should be mitigated by O-DU.
