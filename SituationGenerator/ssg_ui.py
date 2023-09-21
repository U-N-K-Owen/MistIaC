from situationgen import StableSituationGenerator
import argparse
import yaml


class CommandUI:

    ARGUMENTS = {
        "-r": {
            "required": True,
            "metavar": "YAML requests config",
            "help": "Case study requests config in YAML format"
        },
        "-s": {
            "required": True,
            "type": int,
            "metavar": "scale",
            "help": "Scale of requests (2x original, 3x original, etc.). Will be ignored if lower than 1"
        },
        "-o": {
            "required": True,
            "metavar": "Output requests YAML",
            "help": "Output requests in YAML format"
        }
    }

    def __init__(self) -> None:
        self.__ap = argparse.ArgumentParser(
            description="CLI for the Stable Situation Generator", add_help=True)
        for argument in self.ARGUMENTS:
            arg_params = self.ARGUMENTS[argument]
            self.__ap.add_argument(argument, **arg_params)
    
    def launch(self) -> None:
        ui_args = self.__ap.parse_args()
        with open(ui_args.r, 'r') as in_requests:
            requests = yaml.safe_load(in_requests)
        ssg = StableSituationGenerator(requests)
        ssg.generate_situation(ui_args.s, ui_args.o)

if __name__ == '__main__':
    CommandUI().launch()
