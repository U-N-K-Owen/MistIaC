totalTestLength=1800 # 30 minutes
iterMinLength=240 # 4 minutes
requestNumber=5
while [ $requestNumber -le 10 ]; do
sudo systemctl restart docker
sleep 30
docker pull intel/video-analytics-serving:latest
docker pull jellyfin/jellyfin:latest
docker pull linuxserver/grav:latest
cd GravTester
./build.sh
cd ../IntelTester
./build.sh
cd ../JellyfinTester
./build.sh
cd ..
if [ ! -d TestResultInfo ]; then mkdir TestResultInfo; fi
timingReportTag=$(date "+%y-%m-%d-%H-%M-%S")
kind create cluster --config testing-conf-10n.yaml
nodes=$(kubectl get nodes --template='{{range .items}}{{.metadata.name}}{{"\n"}}{{end}}')
while IFS= read -r nodeName; do
    kubectl taint node $nodeName node-role.kubernetes.io/control-plane:NoSchedule-
done <<< "$nodes"
kind load docker-image intel/video-analytics-serving:latest
kind load docker-image jellyfin/jellyfin:latest
kind load docker-image linuxserver/grav:latest
kind load docker-image mistplat/jellyfinrequest:latest
kind load docker-image mistplat/gravrequest:latest
kind load docker-image mistplat/intelairequest:latest
echo "Test type,Request number,Node number" > ./TestResultInfo/TestDescriptor.csv
echo "Native,$requestNumber,10" >> ./TestResultInfo/TestDescriptor.csv
# Generate initial requests
. .venv/bin/activate
cd kubernetes_delegation
./getDeviceInfo.sh
cd ../SituationGenerator
dateTag=$(date "+%y-%m-%d-%H-%M-%S")
latestCheckpoint=../TestResultInfo/usg-checkpoint-$dateTag.pkl
latestRequest=../TestResultInfo/usg-requests-$dateTag.yaml
python3 usg_ui.py -n ../kubernetes_delegation/nodes.yaml -s ../TestingBaseline/services.yaml  -r $requestNumber --checkpoint-save $latestCheckpoint -o $latestRequest
cd ..
echo "Iteration,Date tag,Start time,End time,Time taken (s)" >> ./TestResultInfo/PlatformTimingReport-$timingReportTag.csv
startTime=$(date "+%s")
iterCounter=0
while [ $(expr $(date "+%s") - $startTime) -le $totalTestLength ]; do
    dateTag=$(date "+%y-%m-%d-%H-%M-%S")
    iterStart=$(date "+%s")
    kubectl apply --prune -l mist-type=service -f native-serv-kubeconf.yaml
    cd RequestKube
    python3 r2k_ui.py -r $latestRequest -cs ../TestingBaseline/request_specs.yaml -o ../testing-autogen-cli-kubeconf.yaml
    cd ..
    kubectl apply --prune -l mist-type=request -f testing-autogen-cli-kubeconf.yaml
    cp testing-autogen-cli-kubeconf.yaml ./TestResultInfo/testing-autogen-cli-kubeconf-$dateTag.yaml
    iterEnd=$(date "+%s")
    echo "$iterCounter,$dateTag,$iterStart,$iterEnd,$(expr $iterEnd - $iterStart)" >> ./TestResultInfo/PlatformTimingReport-$timingReportTag.csv
    iterCounter=$(expr $iterCounter + 1)
    cd SituationGenerator
    python3 usg_ui.py --checkpoint-load $latestCheckpoint -r $requestNumber --checkpoint-save ../TestResultInfo/usg-checkpoint-$dateTag.pkl -o ../TestResultInfo/usg-requests-$dateTag.yaml
    cd ..
    kubectl get pods -o wide | tr -s '[:blank:]' ',' > ./TestResultInfo/PodPlacement-$dateTag.csv
    latestCheckpoint=../TestResultInfo/usg-checkpoint-$dateTag.pkl
    latestRequest=../TestResultInfo/usg-requests-$dateTag.yaml
    iterTime=$(expr $(date "+%s") - $iterStart)
    iterLeft=$(expr $iterMinLength - $iterTime)
    if [ $iterLeft -ge 0 ]; then
        sleep $iterLeft
    fi
done
kind delete cluster
cp -a /tmp/hostpath-provisioner/* ./TestResultInfo
sudo rm -rf /tmp/hostpath-provisioner/*
resultDateTag=$(date "+%y-%m-%d-%H-%M-%S")
mv ./TestResultInfo ./TestResultInfo-$resultDateTag
rclone copy "./TestResultInfo-$resultDateTag" "OneDrive:AWSMistResultsPowerful/TestResultInfo-$resultDateTag"
curl -d "Test of 10n-$requestNumber requests done" ntfy.sh/awsmistplatform_dlanor
requestNumber=$(expr $requestNumber + 1)
done
