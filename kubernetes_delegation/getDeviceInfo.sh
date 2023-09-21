#!/bin/bash

csv_file="location.csv"

deg2rad() {
    local degrees="$1"
    local pi=$(echo "scale=10; 4*a(1)" | bc -l)
    local radians=$(echo "scale=10; $degrees * $pi / 180" | bc -l)
    echo "$radians"
}
get_owner() {
    local nodeName="$1"
    local owner_csv_file="owner.csv"
    owner=$(awk -F',' -v value="$nodeName" '$1 == value {print $2}' "$owner_csv_file")
    echo "$owner"
}
get_distance() {
    local myIp="$1"
    local otherIp="$2"
    local csv_file="location.csv"
    # Extract the second and third columns of the matched row
    my_location=$(awk -F',' -v value="$myIp" '$1 == value {print $2, $3}' "$csv_file")
    other_location=$(awk -F',' -v value="$otherIp" '$1 == value {print $2, $3}' "$csv_file")

    # # Print variable declarations with values
    # declare -p my_location
    # declare -p other_location
    
    distance=""
    if [ -n "$my_location" ] && [ -n "$other_location" ]; then
        local lat1=$(echo "$my_location" | cut -d ' ' -f 1)
        local lon1=$(echo "$my_location" | cut -d ' ' -f 2)
        local lat2=$(echo "$other_location" | cut -d ' ' -f 1)
        local lon2=$(echo "$other_location" | cut -d ' ' -f 2)

        local R=6371  # Radius of the Earth in kilometers

        # Convert latitude and longitude from degrees to radians
        local lat1_rad=$(deg2rad "$lat1")
        local lon1_rad=$(deg2rad "$lon1")
        local lat2_rad=$(deg2rad "$lat2")
        local lon2_rad=$(deg2rad "$lon2")

        # Calculate the differences in latitude and longitude
        local dlat=$(echo "$lat2_rad - $lat1_rad" | bc -l)
        local dlon=$(echo "$lon2_rad - $lon1_rad" | bc -l)

        # Calculate the Haversine formula components
        local a=$(echo "s(0.5 * $dlat)^2 + c($lat1_rad) * c($lat2_rad) * s(0.5 * $dlon)^2" | bc -l)
        local c=$(echo "2 * a( sqrt($a) )" | bc -l)

        # Calculate the distance
        local distance=$(echo "$R * $c" | bc -l)

        # Round the distance to the 4th decimal place
        distance=$(printf "%.4f" "$distance")
    fi
    echo "$distance"
}


# name, cpu, memory, 
node_info=$(echo "$(kubectl describe nodes)" | grep -E -A 8 '^Name:|^Allocatable:' | grep -E '^Name:|^  cpu:|^  memory:|^  ephemeral-storage:')

count=0
output="{"
while IFS= read -r line; do
    if (( count % 4 == 0 )); then
        # node name
        name=$(echo "$line" | sed 's/^Name://' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//') # remove leading and trailing whitespace  
        
        # latency
        #podsOfCurNode=$( kubectl get pods  --field-selector=spec.nodeName==$name --template='{{range .items}}{{.metadata.name}}{{"\n"}}{{end}}')
        #ipOfCurNode=$( kubectl get pods --field-selector=spec.nodeName==$name --template='{{range .items}}{{.status.podIP}}{{"\n"}}{{end}}')
        #podsOfOtherNode=$( kubectl get pods --field-selector=spec.nodeName!=$name -o=jsonpath='{range .items[*]}{.status.podIP} {.metadata.name}{"\n"}{end}')
        otherNodes=$(kubectl get nodes --field-selector metadata.name!=$name --template='{{range .items}}{{.metadata.name}}{{"\n"}}{{end}}')
        latency="{"
        location="{"
        #owner
        owner=$(get_owner $name)
        if [ -n "$otherNodes" ]; then
            while IFS= read -r otherNode; do
                distance=$(get_distance "$name" "$otherNode")
                location+="\"$otherNode\":$distance,"
            done <<< "$otherNodes"
            
        fi
        location=${location%,}
        location+="}"
        #if [ -n "$podsOfCurNode" ]; then           
        #    while IFS= read -r otherPods; do
        #        read -r otherPodsIP otherPodsName <<< "$otherPods"
        #        otherNodeName=$(kubectl get pod "$otherPodsName" -o=jsonpath='{.spec.nodeName}')
        #        latencyRaw=$(kubectl exec $podsOfCurNode -- sh -c "ping -c 5 $otherPodsIP")
        #        if [ $? == 0 ]; then
        #            latencyTemp=$(echo "$latencyRaw" | grep -E '^round-trip' | awk -F'/' '{print $(NF-1)}')
        #        else
        #            latencyTemp=0
        #        fi
        #        latency+="\"$otherNodeName\":$latencyTemp,"
        #    done <<< "$podsOfOtherNode"
        #fi
        latency=${latency%,}
        latency+="}"
    elif (( count % 4 == 1 )); then
        # cpu
        cpu=$(echo "$line" | sed 's/cpu://' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//') # remove leading and trailing whitespace
    elif (( count % 4 == 2 )); then
        # storage
        storage=$(echo "$line" | sed 's/ephemeral-storage://' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//'  | sed -e 's/..$//') # remove last two character "Ki"
        storage=$(echo "scale=2; "$storage" / 1024" | bc) #convert Ki to MB
    elif (( count % 4 == 3 )); then
        # ram
        ram=$(echo "$line" | sed 's/memory://' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//'  | sed -e 's/..$//') # remove last two character "Ki"
        ram=$(echo "scale=2; "$ram" / 1024" | bc) #convert Ki to MB
        # output
        output+="\n\"$name\":{\n\"cpu\":$cpu, \n\"ram\":$ram, \n\"storage\":$storage, \n\"owner\":\"$owner\", \n\"latency\":$latency,\n\"location\":$location\n},"
    fi
    (( count++ ))
done <<< "$node_info"

output=${output%,}  # Remove the trailing comma
output+="\n}"
echo -e "$output" > output_device_info.json

python3 json2yaml.py
