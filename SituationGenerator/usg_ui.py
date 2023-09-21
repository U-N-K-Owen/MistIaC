from situationgen import UnstableSituationGenerator
import argparse
import yaml


class CommandUI:

    ARGUMENTS = {
        "-n": {
            "required": False,
            "metavar": "YAML nodes config",
            "help": "Case study nodes config in YAML format. Required if no checkpoint is loaded"
        },
        "-s": {
            "required": False,
            "metavar": "YAML services config",
            "help": "Case study services config YAML configuration. Required if no checkpoint is loaded"
        },
        "-r": {
            "required": True,
            "type": int,
            "metavar": "requests",
            "help": "Number of requests to generate"
        },
        "--rng-seed": {
            "required": False,
            "metavar": "RNG seed",
            "help": "Seed for the random number generator",
            "default": 0
        },
        "--checkpoint-save": {
            "required": False,
            "metavar": "PKL checkpoint",
            "help": "Save the Unstable Situation Generator as a checkpoint in PKL format."
        },
        "--checkpoint-load": {
            "required": False,
            "metavar": "PKL checkpoint",
            "help": "Load the Unstable Situation Generator from a checkpoint in PKL format. Overrides all non-output arguments"
        },
        "-o": {
            "required": True,
            "metavar": "Output requests YAML",
            "help": "Output requests in YAML format"
        }
    }

    def __init__(self) -> None:
        self.__ap = argparse.ArgumentParser(
            description="CLI for the Unstable Situation Generator", add_help=True)
        for argument in self.ARGUMENTS:
            arg_params = self.ARGUMENTS[argument]
            self.__ap.add_argument(argument, **arg_params)
    
    def launch(self) -> None:
        ui_args = self.__ap.parse_args()
        if not ui_args.s or not ui_args.n:
            if not ui_args.checkpoint_load:
                raise TypeError("Must specify at least a checkpoint to load or YAML node and service configurations")
            else:
                usg = UnstableSituationGenerator.load_checkpoint(ui_args.checkpoint_load)
        else:
            with open(ui_args.s, 'r') as in_services:
                services = yaml.safe_load(in_services)
            with open(ui_args.n, 'r') as in_nodes:
                nodes = yaml.safe_load(in_nodes)
            usg = UnstableSituationGenerator(services, nodes, ui_args.rng_seed)
        usg.generate_situation(ui_args.r,  ui_args.o)
        if ui_args.checkpoint_save:
            usg.save_checkpoint(ui_args.checkpoint_save)

if __name__ == '__main__':
    CommandUI().launch()
