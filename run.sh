#!/bin/bash
# Smoke test of the ns-3.48 port: test431.sh (Method #1) parameters, small scale.
# Output is also saved to scratch/wifi-sweet-spot/run.log
cd "$(dirname "$0")/../.." || exit 1

ARGS=(
  --simulationTime=10
  --numberVoIPupload=2
  --numberVoIPdownload=0
  --numberTCPupload=0
  --numberTCPdownload=2
  --numberVideoDownload=0
  --nodeMobility=2
  --constantSpeed=1
  --number_of_APs=4
  --number_of_APs_per_row=2
  --distance_between_APs=50
  --arpAliveTimeout=1.0
  --outputFileName=smoke
  --outputFileSurname=test
  --rateModel=Ideal
  --enablePcap=0
  --generateHistograms=0
  --writeMobility=0
  --numChannels=4
  --verboseLevel=2
  --printSeconds=1
  --version80211=1
  --channelWidth=20
  --wifiModel=1
  --errorRateModel=0
  --propagationLossModel=2
  --topology=2
  --powerLevel=-3
  --prioritiesEnabled=0
  --RtsCtsThreshold=0
  --rateAPsWithAMPDUenabled=1.0
  --aggregationDisableAlgorithm=0
  --aggregationDynamicAlgorithm=1
  --timeMonitorKPIs=0.25
  --latencyBudget=0.004
  --methodAdjustAmpdu=0
  --stepAdjustAmpdu=3000
)

./ns3 run "scratch/wifi-sweet-spot/cc/wifi-central-controlled-aggregation_v199.cc ${ARGS[*]}" 2>&1 \
  | tee scratch/wifi-sweet-spot/run.log
