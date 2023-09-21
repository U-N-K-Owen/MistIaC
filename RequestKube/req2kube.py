import copy
import yaml

class RequestsToKubernetes:

    BASIC_DEPLOYMENT = {
        "apiVersion": "apps/v1",
        "kind": "Deployment"
    }

    BASIC_VOLUME_CLAIM = {
      "apiVersion": "v1",
      "kind": "PersistentVolumeClaim",
      "spec": {
        "storageClassName": "standard",
        "accessModes": ["ReadWriteOnce"],
        "resources": {
          "requests": {
            "storage": "1Gi"
          }
        }
      }
    }

    def __init__(self, requests: "dict[str, dict[str, str]]", request_specs: "dict[str, list[dict[str, Any]]]"):
      self._requests = requests
      self._request_specs = request_specs

    def convert(self, out_yaml: str):
      kube_files = []
      request_pods = list(self._requests.keys())
      for req_name in request_pods:
        deployment_kube_file = self.BASIC_DEPLOYMENT.copy()
        deployment_kube_file["metadata"] = {'name': f'{req_name}-deployment', "labels": {"app": f'{self._requests[req_name]["service"]}-request-app', 'mist-type': 'request'}} # type: ignore
        dep_spec = {"replicas": 1, "selector": {"matchLabels": {"app": f'{self._requests[req_name]["service"]}-request-app', 'mist-type': 'request'}}, "template": {"metadata": {"labels": {"app": f'{self._requests[req_name]["service"]}-request-app', 'mist-type': 'request'}}, "spec": {"affinity": {"nodeAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": {"nodeSelectorTerms": [{"matchExpressions": [{"key": "kubernetes.io/hostname", "operator": "In", "values": [self._requests[req_name]["node"]]}]}]}}}}}}
        container_specs = []
        volume_specs = []
        base_container_specs = self._request_specs[self._requests[req_name]["service"]]
        for idx, base_container in enumerate(base_container_specs):
          peristent_container = copy.deepcopy(base_container)
          peristent_container["volumeMounts"] = [{"name": f'{req_name}-{idx}-volume', 'mountPath': '/persistent/'}]
          volume = {"name": f'{req_name}-{idx}-volume', "persistentVolumeClaim": {"claimName": f'{req_name}-{idx}-claim'}}
          pvc = copy.deepcopy(self.BASIC_VOLUME_CLAIM)
          pvc["metadata"] = {"name": f'{req_name}-{idx}-claim', "labels": {"app": f'{self._requests[req_name]["service"]}-request-app', 'mist-type': 'request'}}
          volume_specs.append(volume)
          container_specs.append(peristent_container)
          kube_files.append(pvc)
        dep_spec["template"]["spec"]["containers"] = container_specs
        dep_spec["template"]["spec"]["volumes"] = volume_specs
        deployment_kube_file["spec"] = dep_spec # type: ignore
        kube_files.append(deployment_kube_file)
      with open(out_yaml, 'w') as out_yaml_stream:
        yaml.safe_dump_all(kube_files, out_yaml_stream)