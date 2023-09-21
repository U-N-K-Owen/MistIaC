from req2kube import RequestsToKubernetes
import argparse
import yaml


class CommandUI:

    ARGUMENTS = {
        "-r": {
            "required": True,
            "metavar": "YAML requests config",
            "help": "Case study requests config in YAML format"
        },
        "-cs": {
            "required": True,
            "metavar": "YAML request container specs",
            "help": "Request container specs YAML configuration"
        },
        "-o": {
            "required": True,
            "metavar": "Output K8s YAML",
            "help": "Output requests in Kubernetes-YAML format"
        }
    }

    def __init__(self) -> None:
        self.__ap = argparse.ArgumentParser(
            description="CLI for the Requests to Kubernetes YAML parser", add_help=True)
        for argument in self.ARGUMENTS:
            arg_params = self.ARGUMENTS[argument]
            self.__ap.add_argument(argument, **arg_params)
    
    def launch(self) -> None:
        ui_args = self.__ap.parse_args()
        with open(ui_args.r, 'r') as in_requests:
            requests = yaml.safe_load(in_requests)
        with open(ui_args.cs, 'r') as in_container_specs:
            container_specs = yaml.safe_load(in_container_specs)
        r2k = RequestsToKubernetes(requests, container_specs)
        r2k.convert(ui_args.o)

if __name__ == '__main__':
    CommandUI().launch()
