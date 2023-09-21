from optimizer import MistPlatformOptimizer
from sol2kube import SolutionToKubernetes
import argparse
import os
import yaml


class CommandUI:

    AVERAGE_OBJ = 'avg'
    MIN_MAX_OBJ = 'minmax'

    OBJECTIVES = [AVERAGE_OBJ, MIN_MAX_OBJ]

    ARGUMENTS = {
        "-n": {
            "required": True,
            "metavar": "YAML node config",
            "help": "Case study nodes config in YAML format"
        },
        "-r": {
            "required": False,
            "metavar": "YAML requests config",
            "help": "Case study requests config in YAML format"
        },
        "-s": {
            "required": True,
            "metavar": "YAML services config",
            "help": "Case study services config in YAML format"
        },
        "-rp": {
            "required": False,
            "metavar": "YAML resource policies",
            "help": "Case study resource policies in YAML format"
        },
        "-sp": {
            "required": False,
            "metavar": "YAML service policies",
            "help": "Case study resource policies in YAML format"
        },
        "--obj": {
            "required": False,
            "help": "Optimization objective",
            "choices": OBJECTIVES,
            "default": AVERAGE_OBJ
        },
        "-cs": {
            "required": False,
            "metavar": "YAML container specs",
            "help": "Container specs YAML configuration. Required if -o is specified"
        },
        "-p": {
            "required": False,
            "metavar": "YAML service ports specification",
            "help": "Service ports YAML configuration. Required if -o is specified"
        },
        "-sm": {
            "required": False,
            "metavar": "YAML service metadata",
            "help": "Service metadata YAML configuration. Defaults to no metadata"
        },
        "--debug": {
            "required": False,
            "metavar": "debug model",
            "help": "Output debug LP model"
        },
        "--dfo": {
            "required": False,
            "metavar": "Output CSV",
            "help": "Output solution dataframe in CSV format"
        },
        "-o": {
            "required": False,
            "metavar": "Output K8s YAML",
            "help": "Output solution in Kubernetes-YAML format"
        }
    }

    def __init__(self) -> None:
        self.__ap = argparse.ArgumentParser(
            description="CLI for the Mist Platform Optimizer", add_help=True)
        for argument in self.ARGUMENTS:
            arg_params = self.ARGUMENTS[argument]
            self.__ap.add_argument(argument, **arg_params)
    
    def launch(self) -> None:
        ui_args = self.__ap.parse_args()
        with open(ui_args.n, 'r') as in_nodes:
            nodes = yaml.safe_load(in_nodes)
        with open(ui_args.s, 'r') as in_services:
            services = yaml.safe_load(in_services)
        if ui_args.r:
            with open(ui_args.r, 'r') as in_requests:
                requests = yaml.safe_load(in_requests)
        else:
            requests = {}
        if ui_args.rp:
            with open(ui_args.rp, 'r') as in_resource_policies:
                resource_policies = yaml.safe_load(in_resource_policies)
        else:
            resource_policies = []
        if ui_args.sp:
            with open(ui_args.sp, 'r') as in_service_policies:
                service_policies = yaml.safe_load(in_service_policies)
        else:
            service_policies = []
        optimizer = MistPlatformOptimizer(nodes, services, requests, resource_policies, service_policies)
        if ui_args.obj == self.AVERAGE_OBJ:
            optimizer.objective_average()
        elif ui_args.obj == self.MIN_MAX_OBJ:
            optimizer.objective_min_max()
        else:
            print('Objective unsupported. Defaulting to average')
            optimizer.objective_average()
        if ui_args.debug:
            optimizer.debug(ui_args.debug)
        optimization_ok = optimizer.optimize()
        if optimization_ok:
            sol_df = optimizer.get_solution_dataframe()
            if ui_args.dfo:
                sol_df.to_csv(ui_args.dfo, index=False)
            if ui_args.o:
                if not ui_args.cs:
                    raise ValueError("Container specs must be specified")
                with open(ui_args.cs, 'r') as in_container_specs:
                    container_specs = yaml.safe_load(in_container_specs)

                if not ui_args.p:
                    raise ValueError("Service ports must be specified")
                with open(ui_args.p, 'r') as in_ports:
                    service_ports = yaml.safe_load(in_ports)
                
                if ui_args.sm:
                    with open(ui_args.sm, 'r') as in_service_meta:
                        service_metadata  = yaml.safe_load(in_service_meta)
                else:
                    service_metadata = {}
                s2k = SolutionToKubernetes(sol_df, container_specs, service_ports, service_metadata)
                s2k.convert(ui_args.o)

if __name__ == '__main__':
    CommandUI().launch()
