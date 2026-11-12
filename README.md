# wifi-sweet-spot ns3
ns3 scripts for simulating scenarios in which dynamic 802.11 frame aggregation is studied.

A previous version of this study can be found here: https://github.com/Wi5/ns3_802.11_frame_aggregation


## Citation
If you use this code, please cite the next research article (final reference still pending):

Jose Saldana, Omer Topal, Jose Ruiz-Mas, Julian Fernandez-Navajas, "Finding the Sweet Spot for Frame Aggregation in 802.11 WLANs," in IEEE Communications Letters, vol. 25, no. 4, pp. 1368-1372, April 2021, doi: [10.1109/LCOMM.2020.3044231](https://doi.org/10.1109/LCOMM.2020.3044231)

https://ieeexplore.ieee.org/document/9291427

Author's self-archive version: https://github.com/wifi-sweet-spot/ns3/blob/main/LCOMM3044231_authors_version.pdf


## Content of the repository

The `cc` folder contains the ns3 script. It has been run with ns3-30.1 (https://www.nsnam.org/releases/ns-3-30/).

`wifi-central-controlled-aggregation_v199.cc` is the main ns3 file used for the paper.

`wifi-central-controlled-aggregation_v215.cc` has also been used.

In addition, for some tests, these other versions with other coefficients have been employed:
```
wifi-central-controlled-aggregation_v199b11.cc 
wifi-central-controlled-aggregation_v199b12.cc
wifi-central-controlled-aggregation_v199b13.cc
wifi-central-controlled-aggregation_v199b14.cc
wifi-central-controlled-aggregation_v199b15.cc
wifi-central-controlled-aggregation_v199b16.cc
```

The `sh` folder contains the files used for obtaining each of the figures presented in the paper.

- Figure 1 was obtained with `test451.sh`, 1 user, seed 2.

- Figure 2a) was obtained with `test451.sh`, 1 user seed 2.

- Figure 2b) was obtained with `test452.sh`, 1 user seed 2.

- Figure 2c) was obtained with `test453.sh`, 1 user seed 2.

- Figure 3 was obtained with `test453.sh`, 1 user seed 2.

- Figures 4 to 7 were obtained with the next scripts:

`test411.sh`. No aggregation (1). Version 199

`test412.sh`. Aggregation always active (2). Version 199

`test414.sh`. Disable algorithm (3). Version 199

`test431.sh`. Method #1: linear decrease, linear increase (4). Version 199

`test521.sh`. Method #2: geometric decrease, geometric increase (5). Version 199b11

`test432.sh`. Method #3: drastic reduction to minimum, linear increase (6). Versiion 199

`test434.sh`. Method #4: linear decrease, drastic increase to maximum (7). Version 215


- Figure 8 (method #1) was obtained with the next scripts:

`test481`, `test431`, `test482`, `test483`, `test484`.

- Figure 9 (method #2) was obtained with the next scripts

`test521.sh` (Version 199b11), `test522.sh` (Version 199b12), `test523.sh` (Version 199b13), `test524.sh` (Version 199b14), `test525.sh` (Version 199b15), `test526.sh` (Version 199b16), 

## How to use it

- Download ns3.

- Put the `.cc` file in the `ns-3.30.1/scratch` directory.

- Put a `.sh` file in the `ns-3.30.1` directory.

- Run a `.sh` file. (You may need to adjust the name of the `.cc` file in the `.sh` script).

## Ported to ns-3.48

The scripts in `cc/` have been ported from ns-3.30.1 to ns-3.48 (the original
ns-3.30 versions are in the git history). Changes:

| ns-3.30.1 | ns-3.48 |
|---|---|
| `YansWifiPhyHelper::Default ()`, `SpectrumWifiPhyHelper::Default ()` | plain constructors |
| `WIFI_PHY_STANDARD_80211n_5GHZ` / `_2_4GHZ` / `80211ac` / `80211g` / `80211a` | `WIFI_STANDARD_80211n` / `80211ac` / `80211g` / `80211a`; the band is now given by the channel |
| PHY attributes `ChannelNumber`, `ChannelWidth` (now read-only) and `WifiPhy::SetChannelNumber ()` (removed) | `ChannelSettings` attribute, built by the helper `ChannelSettingsStr ()` (channels 1-14 -> 2.4 GHz / 20 MHz; others -> 5 GHz / `--channelWidth`) |
| PHY attribute `ShortGuardEnabled` | removed (short GI is disabled by default) |
| `ns3::WifiPhy::EnergyDetectionThreshold` | `ns3::WifiPhy::RxSensitivity` |
| Config paths with `$ns3::RegularWifiMac/` | removed from the path (`.../Mac/BE_MaxAmpduSize`, `.../Mac/$ns3::StaWifiMac/Assoc`) |
| `TcpWestwood` + `ProtocolType=WESTWOODPLUS` | `TcpWestwoodPlus` |
| `Ptr == 0`, `isnan` | `Ptr == nullptr`, `std::isnan` |
| `InetSocketAddress::SetTos ()` (removed) | `Tos` attribute of the client application (`UdpClient`, `BulkSend`, `UdpTraceClient`) |
| `UdpTraceClientHelper (socketAddress, port, "")` | `UdpTraceClientHelper (socketAddress, "")` (the 3-argument form now aborts if given a socket address) |
| VLA `FlowStatistics x[n]` passed to `Simulator::Schedule` | `static_cast<FlowStatistics*> (x)` |
| STA->AP matching with a hard-coded `"02-06-" << mac` prefix | `Address (mac)`, the same format used for the AP records (the `Address` type id of `Mac48Address` is 01 in ns-3.48, so the hard-coded prefix never matched: no STA was ever found under its AP and the algorithms saw a VoIP latency of 0) |
| (v215) `WifiPhyStandard`-based band detection | `getWirelessBandOfVersion ()`, based on the version string |

Important: with `$ns3::RegularWifiMac` in the path, `Config::Set` in ns-3.48
matches no object and silently does nothing, i.e. the dynamic A-MPDU algorithm
would have no effect. `ModifyAmpdu ()` now uses `Config::SetFailSafe` and aborts
if the path matches nothing.

`CMakeLists.txt` builds every `cc/*.cc` as a separate program. The `sh/` scripts
now call `./ns3 run` and can be launched from any directory (they `cd` to the
ns-3 root, where the output files are written).

```bash
./ns3 configure --build-profile=optimized
./ns3 build
bash scratch/wifi-sweet-spot/sh/test431.sh
```

Note: the PHY/MAC models changed between ns-3.30 and ns-3.48, so the results
are expected to follow the same trends as the paper, not to be identical.
