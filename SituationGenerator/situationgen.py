import pickle
import random
import yaml
import copy

class UnstableSituationGenerator:

    @staticmethod
    def load_checkpoint(checkpoint_filename: str) -> "UnstableSituationGenerator":
        with open(checkpoint_filename, 'rb') as in_pkl:
            usg = pickle.load(in_pkl)
        return usg

    def __init__(self, services: "dict[str, dict[str, str|int|float|dict[str, str|int|float]]]", nodes: "dict[str, dict[str, str|int|float|dict[str, str|int|float]]]", rng_seed = 0):
        self._services = services
        self._nodes = nodes
        self._rng = random.Random(rng_seed)
    
    def generate_situation(self, num_requests: int, out_yaml: str):
        generated_requests = {}
        chosen_requestors = self._rng.choices(list(self._nodes.keys()), k=num_requests)
        chosen_services = self._rng.choices(list(self._services.keys()), k=num_requests)
        pair_ids = {}
        for requestor, service in zip(chosen_requestors, chosen_services):
            pair_ids[(requestor, service)] = pair_ids.get((requestor, service), 0) + 1
            req_id = f'{requestor}-{service}-{pair_ids[(requestor, service)]}'
            generated_requests[req_id] = {"node": requestor, "service": service}
        with open(out_yaml, 'w') as out_file:
            yaml.safe_dump(generated_requests, out_file)

    def save_checkpoint(self, checkpoint_filename: str):
        with open(checkpoint_filename, 'wb') as out_pkl:
            pickle.dump(self, out_pkl)

class StableSituationGenerator:

    def __init__(self, requests: "dict[str, dict[str, str]]"):
        self._requests = requests
    
    def generate_situation(self, scale: int, out_yaml: str):
        generated_requests = copy.deepcopy(self._requests)
        scale -= 1
        while scale >= 1:
            for og_request_name in self._requests:
                additional_request = copy.deepcopy(self._requests[og_request_name])
                additional_request_name = f'{og_request_name}-{scale}'
                generated_requests[additional_request_name] = additional_request
            scale -= 1
        with open(out_yaml, 'w') as out_file:
            yaml.safe_dump(generated_requests, out_file)