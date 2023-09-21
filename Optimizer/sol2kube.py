import yaml
import copy
import pandas as pd

class SolutionToKubernetes:

  BASIC_SERVICE = {
      "apiVersion": 'v1',
      "kind": 'Service',
      "spec": {
          "type": 'NodePort'
      }
  }

  BASIC_DEPLOYMENT = {
      "apiVersion": "apps/v1",
      "kind": "Deployment"
  }

  def __init__(self, solution: pd.DataFrame, container_specs: "dict[str, list[dict[str, Any]]]", service_ports: "dict[str, int]", service_meta: "dict[str, dict[str, Any]]" = {}):
    self._solution = solution
    self._container_specs = container_specs
    self._service_ports = service_ports
    self._service_meta = service_meta

  def convert(self, out_yaml: str):
    kube_files = []
    services_to_deploy = list(self._solution["Service"].unique())
    for service in services_to_deploy:
      service_kube_file = self.BASIC_SERVICE.copy()
      service_kube_file['metadata'] = {"name": f'{service}-service', 'labels': {'mist-type': 'service'}}
      service_kube_file["spec"]["selector"] = {"app": f'{service}-app'}
      service_kube_file["spec"]["ports"] = [{"protocol": "TCP", "name": f"{service}-service-port", "port": self._service_ports[service], "targetPort": self._service_ports[service]}]
      nodes_to_replicate_in = list(self._solution.query('Service == @service')["Deployment node"].unique())
      deployment_kube_file = self.BASIC_DEPLOYMENT.copy()
      dep_labels = copy.deepcopy(self._service_meta.get(service, {}))
      dep_labels["app"] = f'{service}-app'
      dep_labels['mist-type'] = 'service'
      deployment_kube_file["metadata"] = {"name": f'{service}-deployment', "labels": dep_labels}
      dep_spec = {"replicas": len(nodes_to_replicate_in), "selector": {"matchLabels": {"app": f'{service}-app', 'mist-type': 'service'}}, "template": {"metadata": {"labels": {"app": f'{service}-app', 'mist-type': 'service'}}, "spec": {"affinity": {"nodeAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": {"nodeSelectorTerms": []}}}, "containers": self._container_specs[service]}}}
      for node in nodes_to_replicate_in:
        matcher = {"matchExpressions": [{"key": "kubernetes.io/hostname", "operator": "In", "values": [node]}]}
        dep_spec["template"]["spec"]["affinity"]["nodeAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"]["nodeSelectorTerms"].append(matcher)
      deployment_kube_file["spec"] = dep_spec
      kube_files.append(deployment_kube_file)
      kube_files.append(copy.deepcopy(service_kube_file))
    with open(out_yaml, 'w') as out_yaml_stream:
      yaml.safe_dump_all(kube_files, out_yaml_stream)