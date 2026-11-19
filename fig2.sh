#!/bin/bash
# Reproduce the runs behind Fig. 2 (README: test451/452/453, 1 user, seed 2):
#   1 AP, 1 TCP download user + 1 VoIP upload user, 180 s, RngRun=2
#   fig2a: no aggregation        (test451)
#   fig2b: aggregation always on (test452)
#   fig2c: dynamic algorithm, Method #1 (methodAdjustAmpdu=0), as stated in the
#          paper text. Note: test453.sh uses methodAdjustAmpdu=3 (Method #2).
# Then plot them with plot_fig2.py -> scratch/wifi-sweet-spot/fig2.png
cd "$(dirname "$0")/../.." || exit 1

COMMON=(
  --simulationTime=180
  --numberVoIPupload=1 --numberVoIPdownload=0
  --numberTCPupload=0 --numberTCPdownload=1 --numberVideoDownload=0
  --nodeMobility=2 --constantSpeed=1
  --number_of_APs=1 --number_of_APs_per_row=1 --distance_between_APs=50
  --arpAliveTimeout=1.0
  --outputFileSurname=seed-2
  --rateModel=Ideal --enablePcap=0 --generateHistograms=0 --writeMobility=1
  --numChannels=16 --verboseLevel=0 --printSeconds=30
  --version80211=1 --channelWidth=20 --wifiModel=1 --errorRateModel=0
  --propagationLossModel=2 --topology=2 --powerLevel=-3
  --prioritiesEnabled=0 --RtsCtsThreshold=0
)

run() {
  local name=$1; shift
  rm -f "${name}"_* # outputs are appended to, so start clean
  echo "=== ${name} $(date)"
  NS_GLOBAL_VALUE="RngRun=2" ./ns3 run \
    "wifi-central-controlled-aggregation_v199 ${COMMON[*]} --outputFileName=${name} $*" || exit 1
}

run fig2a --rateAPsWithAMPDUenabled=0.0 --aggregationDisableAlgorithm=0
run fig2b --rateAPsWithAMPDUenabled=1.0 --aggregationDisableAlgorithm=0 --aggregationDynamicAlgorithm=0
run fig2c --rateAPsWithAMPDUenabled=1.0 --aggregationDisableAlgorithm=0 \
          --aggregationDynamicAlgorithm=1 --timeMonitorKPIs=0.25 --latencyBudget=0.004 \
          --methodAdjustAmpdu=0 --stepAdjustAmpdu=3000

scratch/lab/.venv/bin/python scratch/wifi-sweet-spot/plot_fig2.py
