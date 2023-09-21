import requests
import pandas as pd
import time
import datetime
import sys

date_id = datetime.datetime.now().strftime("%y-%m-%d-%H-%M-%S")

wait_ready_url = "http://intelai-service.default.svc.cluster.local:8080/pipelines"

time_report_data = []

print("Waiting until the system is ready...")
sys.stdout.flush()
sys.stderr.flush()
system_ready = False
while not system_ready:
    try:
        response = requests.get(wait_ready_url)
        if response.status_code == 200:
            system_ready = True
    except Exception:
        pass

print(f"System is ready")
sys.stdout.flush()
sys.stderr.flush()

iter_counter = 0
while True:
    url = wait_ready_url+"/object_detection/person_vehicle_bike"

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "source": {
            "uri": "https://github.com/intel-iot-devkit/sample-videos/blob/master/person-bicycle-car-detection.mp4?raw=true",
            "type": "uri"
        },
        "parameters": {
            "threshold": 0.75
        },
        "destination": {
            "metadata": {
                "type": "file",
                "path": "/tmp/detection_results.json",
                "format": "json-lines"
            }
        }
    }

    print(f"Sending request")
    sys.stdout.flush()
    sys.stderr.flush()

    start_time = time.perf_counter()

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        print("Pipeline request was successful.")
        print("Pipeline request ID:", response.content)
        sys.stdout.flush()
        sys.stderr.flush()
    else:
        print("Request failed with status code:", response.status_code)
        print("Response content:", response.content)
        sys.stdout.flush()
        sys.stderr.flush()
        raise ValueError(f"Request failed with status code {response.status_code}")

    request_num = response.content

    check_url = url+f"/{request_num.decode()[:-1]}/status"

    request_over = False

    print("Waiting until the pipeline finishes...")
    sys.stdout.flush()
    sys.stderr.flush()
    while not request_over:
        response = requests.get(check_url)
        if response.status_code == 200:
            json_response = response.json()
            state = json_response["state"]
            if state == "COMPLETED":
                end_time = time.perf_counter()
                request_over = True
                print("Pipeline finished")
                sys.stdout.flush()
                sys.stderr.flush()
                time_report_data.append({"Iteration": iter_counter, "Start time": start_time, "End time": end_time, "Time taken (s)": end_time-start_time})
        else:
            print("Checking request failed with status code:", response.status_code)
            print("Response content:", response.content)
            sys.stdout.flush()
            sys.stderr.flush()
            raise ValueError(f"Request failed with status code {response.status_code}")
    pd.DataFrame(time_report_data).to_csv(f"/persistent/IntelAIQoS-{date_id}.csv", index=False) # Refresh on disk
    iter_counter += 1