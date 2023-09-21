from typing import Union
from mip.model import *
from mip.constants import OptimizationStatus
import numpy as np
import pandas as pd

class MistPlatformOptimizer:

  def __init__(self, nodes: "dict[str, dict[str, Union[str, int, float, dict[str, Union[int, float]]]]]", services: "dict[str, dict[str, Union[str, int, float, dict[str, Union[str, int, float]]]]]", requests: "dict[str, dict[str, str]]", resource_policies: "list[dict[str, Union[str, int, float, list[str], dict[str, Union[int, float, str]]]]]", service_policies: "list[dict[str, Union[str, list[str], dict[str, Union[int, float, str]]]]]"):
      self._model = Model("MistPlatformOpt")
      self._nodes = nodes if nodes is not None else {}
      for node_id in self._nodes:
          self._nodes[node_id]["id"] = node_id
      self._services = services if services is not None else {}
      for service_id in self._services:
          self._services[service_id]["id"] = service_id
      self._requests = requests if requests is not None else {}
      for request_id in self._requests:
        self._requests[request_id]["id"] = request_id
      self._resource_policies = resource_policies if resource_policies is not None else []
      for policy in resource_policies if resource_policies is not None else []:
        if policy["user"] != self._nodes[policy["node"]]["owner"]:
          self._resource_policies.remove(policy)
      self._service_policies = service_policies if service_policies is not None else []
      for policy in service_policies if service_policies is not None else []:
        if policy["developer"] != self._services[policy["service"]]["developer"]:
          self._service_policies.remove(policy)
      self._z_vars = self._create_z_vars()
      self._max_z_subvars = self._create_max_z_subvars()
      self._create_constraints()
      self._objective_locked = False
      self._optimized = False

  def _create_z_vars(self) -> "dict[str, dict[str, mip.Var]]":
    return {r: {n: self._model.add_var(name=f'z_{r}_{n}', var_type=mip.BINARY) for n in self._nodes} for r in self._requests}

  def _create_max_z_subvars(self) -> "dict[str, dict[str, mip.Var]]":
    max_z_subvars = {n: {s: self._model.add_var(name=f'max_z_{n}_{s}', var_type=mip.BINARY) for s in self._services} for n in self._nodes}
    for n in self._nodes:
      for s in self._services:
        n_var_collect = []
        for r in self._z_vars:
          if s == self._requests[r]["service"]:
            n_var_collect.append(self._z_vars[r][n])
        self._model.add_constr(max_z_subvars[n][s] <= xsum(n_var_collect), name=f'max_subvar_sum_{n}_{s}')
        for ndx, var in enumerate(n_var_collect):
          self._model.add_constr(max_z_subvars[n][s] >= var, name=f'max_subvar_{n}_{s}_{ndx}')
    return max_z_subvars

  def _create_constraints(self):
    self._request_fulfillment_constraint()
    self._ram_limit_constraint()
    self._cpu_limit_constraint()
    self._storage_limit_constraint()
    self._allowed_developers_constraint()
    self._allowed_requestors_constraint()
    self._maximum_distance_constraint()
    self._maximum_latency_constraint()
    self._forced_metadata_resource_constraint()
    self._upper_bound_metadata_resource_constraint()
    self._lower_bound_metadata_resource_constraint()
    self._forced_metadata_service_constraint()
    self._upper_bound_metadata_service_constraint()
    self._lower_bound_metadata_service_constraint()
    self._allowed_owners_constraint()

  def _request_fulfillment_constraint(self):
    for r in self._requests:
      self._model.add_constr(xsum(self._z_vars[r][n] for n in self._nodes) == 1, name=f'request_fulfillment_{r}')

  def _ram_limit_constraint(self):
    for n in self._nodes:
      consumed_ram = xsum(self._services[s]["ram"]*self._max_z_subvars[n][s] for s in self._services)
      relevant_rp = list(filter(lambda rp: rp["node"] == n in rp, self._resource_policies))
      if len(relevant_rp) > 0:
        min_ram = min([rp.get("max_ram", 100) for rp in (relevant_rp if len(relevant_rp) > 0 else [{}])])/100
        self._model.add_constr(consumed_ram <= min_ram*self._nodes[n]["ram"], name=f'ram_limit_{n}')

  def _cpu_limit_constraint(self):
    for n in self._nodes:
      consumed_cpu = xsum(self._services[s]["cpu"]*self._max_z_subvars[n][s] for s in self._services)
      relevant_rp = list(filter(lambda rp: rp["node"] == n in rp, self._resource_policies))
      if len(relevant_rp) > 0:
        min_cpu = min([rp.get("max_cpu", 100) for rp in (relevant_rp if len(relevant_rp) > 0 else [{}])])/100
        self._model.add_constr(consumed_cpu <= min_cpu*self._nodes[n]["cpu"], name=f'cpu_limit_{n}')

  def _storage_limit_constraint(self):
    for n in self._nodes:
      consumed_storage = xsum(self._services[s]["storage"]*self._max_z_subvars[n][s] for s in self._services)
      relevant_rp = list(filter(lambda rp: rp["node"] == n in rp, self._resource_policies))
      if len(relevant_rp) > 0:
        min_storage = min([rp.get("max_storage", 100) for rp in (relevant_rp if len(relevant_rp) > 0 else [{}])])/100
        self._model.add_constr(consumed_storage <= min_storage*self._nodes[n]["storage"], name=f'storage_limit_{n}')

  def _allowed_developers_constraint(self):
    for s in self._services:
      idx = 0
      for rp in self._resource_policies:
        if "allowed_developers" in rp:
          idx += 1
          self._model.add_constr(self._max_z_subvars[rp["node"]][s] <= (1 if self._services["developer"] in rp["allowed_developers"] else 0), name=f'allowed_developers_{s}_{idx}')

  def _allowed_requestors_constraint(self):
    for r in self._requests:
      idx = 0
      for rp in self._resource_policies:
        if "allowed_users" in rp:
          idx += 1
          self._model.add_constr(self._z_vars[r][rp["node"]] <= (1 if self._nodes[self._requests[r]["node"]]["owner"] in rp["allowed_users"] else 0), name=f'allowed_requestors_{r}_{idx}')

  def _maximum_distance_constraint(self):
    for r in self._requests:
      idx = 0
      for rp in self._resource_policies:
        if "max_distance" in rp:
          idx += 1
          self._model.add_constr(self._z_vars[r][rp["node"]]*self._nodes[rp["node"]]["location"].get(self._requests[r]["node"], 0) <= rp["max_distance"], name=f'max_distance_{r}_{idx}')

  def _maximum_latency_constraint(self):
    for r in self._requests:
      idx = 0
      for rp in self._resource_policies:
        if "max_latency" in rp:
          idx += 1
          self._model.add_constr(self._z_vars[r][rp["node"]]*self._nodes[rp["node"]]["latency"].get(self._requests[r]["node"], 0) <= rp["max_latency"], name=f'max_latency_{r}_{idx}')

  def _forced_metadata_resource_constraint(self):
    for s in self._services:
      idx = 0
      for rp in self._resource_policies:
        if "forced_metadata" in rp:
          idx += 1
          meq = 1 if all([rp["forced_metadata"][k] == self._services[s]["metadata"].get(k) for k in rp["forced_metadata"]]) else 0
          self._model.add_constr(self._max_z_subvars[rp["node"]][s] <= meq, name=f'forced_metadata_resource_{s}_{idx}')

  def _upper_bound_metadata_resource_constraint(self):
    for s in self._services:
      idx = 0
      for rp in self._resource_policies:
        if "upper_bound_metadata" in rp:
          idx += 1
          mle = 1 if all([rp["upper_bound_metadata"][k] >= self._services[s]["metadata"].get(k) for k in rp["upper_bound_metadata"]]) else 0
          self._model.add_constr(self._max_z_subvars[rp["node"]][s] <= mle, name=f'upper_bound_metadata_resource_{s}_{idx}')

  def _lower_bound_metadata_resource_constraint(self):
    for s in self._services:
      idx = 0
      for rp in self._resource_policies:
        if "lower_bound_metadata" in rp:
          idx += 1
          mge = 1 if all([rp["lower_bound_metadata"][k] <= self._services[s]["metadata"].get(k) for k in rp["lower_bound_metadata"]]) else 0
          self._model.add_constr(self._max_z_subvars[rp["node"]][s] <= mge, name=f'lower_bound_metadata_resource_{s}_{idx}')

  def _forced_metadata_service_constraint(self):
    for n in self._nodes:
      idx = 0
      for sp in self._service_policies:
        if "forced_metadata" in sp:
          idx += 1
          meq = 1 if all([sp["forced_metadata"][k] == self._nodes[n]["metadata"].get(k) for k in sp["forced_metadata"]]) else 0
          self._model.add_constr(self._max_z_subvars[n][sp["service"]] <= meq, name=f'forced_metadata_service_{n}_{idx}')

  def _upper_bound_metadata_service_constraint(self):
    for n in self._nodes:
      idx = 0
      for sp in self._service_policies:
        if "upper_bound_metadata" in sp:
          idx += 1
          mle = 1 if all([sp["upper_bound_metadata"][k] >= self._nodes[n]["metadata"].get(k) for k in sp["upper_bound_metadata"]]) else 0
          self._model.add_constr(self._max_z_subvars[n][sp["service"]] <= mle, name=f'upper_bound_metadata_service_{n}_{idx}')

  def _lower_bound_metadata_service_constraint(self):
    for n in self._nodes:
      idx = 0
      for sp in self._service_policies:
        if "lower_bound_metadata" in sp:
          idx += 1
          mge = 1 if all([sp["lower_bound_metadata"][k] <= self._nodes[n]["metadata"].get(k) for k in sp["lower_bound_metadata"]]) else 0
          self._model.add_constr(self._max_z_subvars[n][sp["service"]] <= mge, name=f'lower_bound_metadataservice_{n}_{idx}')

  def _allowed_owners_constraint(self):
    for n in self._nodes:
      idx = 0
      for sp in self._service_policies:
        if "allowed_owners" in sp:
          idx += 1
          self._model.add_constr(self._max_z_subvars[n][sp["service"]] <= (1 if self._nodes["owner"] in sp["allowed_owners"] else 0), name=f'allowed_owners_{n}_{idx}')

  def _upper_bound_distances_resource(self) -> "list[mip.LinExpr]":
    ub_distances_list = []
    for rp in self._resource_policies:
      if "upper_bound_metadata" in rp:
        for k in rp["upper_bound_metadata"]:
          relevant_rps = list(filter(lambda x: k in x["upper_bound_metadata"], self._resource_policies))
          if len(relevant_rps) > 0:
            max_ub = max([rp_ub["upper_bound_metadata"][k] for rp_ub in relevant_rps])
            for r in self._requests:
              if k in self._services[self._requests[r]["service"]]["metadata"]:
                dist_metric = np.interp((rp["upper_bound_metadata"][k] - self._services[self._requests[r]["service"]]["metadata"][k]), [0, max_ub], [0, 1])
                linexpr = rp["upper_bound_metadata"][k] - ((rp["upper_bound_metadata"][k] - dist_metric)*self._z_vars[r][rp["node"]])
                ub_distances_list.append(linexpr)
    return ub_distances_list

  def _lower_bound_distances_resource(self) -> "list[mip.LinExpr]":
    lb_distances_list = []
    for rp in self._resource_policies:
      if "lower_bound_metadata" in rp:
        for k in rp["lower_bound_metadata"]:
          relevant_rps = list(filter(lambda x: k in self._requests[x]["metadata"], self._requests))
          if len(relevant_rps) > 0:
            max_meta = max([self._requests[r_lb]["metadata"][k] for r_lb in relevant_rps])
            for r in self._requests:
              if k in self._services[self._requests[r]["service"]]["metadata"]:
                dist_metric = np.interp((self._services[self._requests[r]["service"]]["metadata"][k] - rp["lower_bound_metadata"][k]), [0, max_meta], [0, 1])
                linexpr = self._services[self._requests[r]["service"]]["metadata"][k] - ((self._services[self._requests[r]["service"]]["metadata"][k] - dist_metric)*self._z_vars[r][rp["node"]])
                lb_distances_list.append(linexpr)
    return lb_distances_list

  def _upper_bound_distances_service(self) -> "list[mip.LinExpr]":
    ub_distances_list = []
    for sp in self._service_policies:
      if "upper_bound_metadata" in sp:
        for k in sp["upper_bound_metadata"]:
          relevant_sps = list(filter(lambda x: k in x["upper_bound_metadata"], self._service_policies))
          if len(relevant_sps) > 0:
            max_ub = max([sp_ub["upper_bound_metadata"][k] for sp_ub in relevant_sps])
            for r in self._requests:
              if self._requests[r]["service"] == sp["service"]:
                for n in self._nodes:
                  if k in self._nodes[n]["metadata"]:
                    dist_metric = np.interp((sp["upper_bound_metadata"][k] - self._nodes[n]["metadata"][k]), [0, max_ub], [0, 1])
                    linexpr = sp["upper_bound_metadata"][k] - ((sp["upper_bound_metadata"][k] - dist_metric)*self._z_vars[r][n])
                    ub_distances_list.append(linexpr)
    return ub_distances_list

  def _lower_bound_distances_service(self) -> "list[mip.LinExpr]":
    lb_distances_list = []
    for sp in self._service_policies:
      if "lower_bound_metadata" in sp:
        for k in sp["lower_bound_metadata"]:
          relevant_sps = list(filter(lambda x: k in self._nodes[x]["metadata"], self._nodes))
          if len(relevant_sps) > 0:
            max_lb = max([self._nodes[n_lb]["metadata"][k] for n_lb in relevant_sps])
            for r in self._requests:
              if self._requests[r]["service"] == sp["service"]:
                for n in self._nodes:
                  if k in self._nodes[n]["metadata"]:
                    dist_metric = np.interp((self._nodes[n]["metadata"][k] - sp["lower_bound_metadata"][k]), [0, max_lb], [0, 1])
                    linexpr = self._nodes[n]["metadata"][k] - ((self._nodes[n]["metadata"][k] - dist_metric)*self._z_vars[r][n])
                    lb_distances_list.append(linexpr)
    return lb_distances_list

  def _distance_distances(self) -> "list[mip.LinExpr]":
    distances = []
    for rp in self._resource_policies:
      if "max_distance" in rp:
        for r in self._requests:
          distances.append((rp["max_distance"] - self._z_vars[r][rp["node"]]*self._nodes[rp["node"]]["location"].get(self._requests[r]["node"], 0))/rp["max_distance"])
    return distances

  def _distance_latencies(self) -> "list[mip.LinExpr]":
    latencies = []
    for rp in self._resource_policies:
      if "max_latency" in rp:
        for r in self._requests:
          latencies.append((rp["max_latency"] - self._z_vars[r][rp["node"]]*self._nodes[rp["node"]]["latency"].get(self._requests[r]["node"], 0))/rp["max_latency"])
    return latencies

  def _ram_availables(self) -> "list[mip.LinExpr]":
    rams = []
    for n in self._nodes:
      node_rps = list(filter(lambda x: x["node"] == n, self._resource_policies))
      if len(node_rps) > 0:
        min_ram = min([rp.get("max_ram", 100) for rp in node_rps])
      else:
        min_ram = 100
      min_ram = min_ram/100
      min_ram_term = min_ram/self._nodes[n]["ram"]
      service_ram = xsum((self._services[s]["ram"]/self._nodes[n]["ram"])*self._max_z_subvars[n][s] for s in self._services)
      rams.append(min_ram_term-service_ram)
    return rams

  def _cpu_availables(self) -> "list[mip.LinExpr]":
    cpus = []
    for n in self._nodes:
      node_rps = list(filter(lambda x: x["node"] == n, self._resource_policies))
      if len(node_rps) > 0:
        min_cpu = min([rp.get("max_cpu", 100) for rp in node_rps])
      else:
        min_cpu = 100
      min_cpu = min_cpu/100
      min_cpu_term = min_cpu/self._nodes[n]["cpu"]
      service_cpu = xsum((self._services[s]["cpu"]/self._nodes[n]["cpu"])*self._max_z_subvars[n][s] for s in self._services)
      cpus.append(min_cpu_term-service_cpu)
    return cpus

  def _storage_availables(self) -> "list[mip.LinExpr]":
    storages = []
    for n in self._nodes:
      node_rps = list(filter(lambda x: x["node"] == n, self._resource_policies))
      if len(node_rps) > 0:
        min_storage = min([rp.get("max_storage", 100) for rp in node_rps])
      else:
        min_storage = 100
      min_storage = min_storage/100
      min_storage_term = min_storage/self._nodes[n]["storage"]
      service_storage = xsum((self._services[s]["storage"]/self._nodes[n]["storage"])*self._max_z_subvars[n][s] for s in self._services)
      storages.append(min_storage_term-service_storage)
    return storages

  def objective_average(self):
    if not self._objective_locked:
      self._objective_locked = True
      obj = self._upper_bound_distances_resource() + self._lower_bound_distances_resource() + self._upper_bound_distances_service() + self._lower_bound_distances_service() + self._distance_distances() + self._distance_latencies() + self._ram_availables() + self._cpu_availables() + self._storage_availables()
      self._model.objective=maximize(xsum(obj))

  def objective_min_max(self):
    if not self._objective_locked:
      self._objective_locked = True
      ub_rp_var = self._model.add_var(name="ub_rp")
      for idx, ub_rp in enumerate(self._upper_bound_distances_resource()):
        self._model.add_constr(ub_rp_var <= ub_rp, name=f'ub_rp_{idx}')
      lb_rp_var = self._model.add_var(name="lb_rp")
      for idx, lb_rp in enumerate(self._lower_bound_distances_resource()):
        self._model.add_constr(lb_rp_var <= lb_rp, name=f'lb_rp_{idx}')
      ub_sp_var = self._model.add_var(name="ub_sp")
      for idx, ub_sp in enumerate(self._upper_bound_distances_resource()):
        self._model.add_constr(ub_sp_var <= ub_sp, name=f'ub_sp_{idx}')
      lb_sp_var = self._model.add_var(name="lb_sp")
      for idx, lb_sp in enumerate(self._lower_bound_distances_resource()):
        self._model.add_constr(lb_sp_var <= lb_sp, name=f'lb_sp_{idx}')
      dist_var = self._model.add_var(name="dist")
      for idx, dist in enumerate(self._distance_distances()):
        self._model.add_constr(dist_var <= dist, name=f'dist_{idx}')
      lat_var = self._model.add_var(name="lat")
      for idx, lat in enumerate(self._distance_latencies()):
        self._model.add_constr(lat_var <= lat, name=f'lat_{idx}')
      ram_var = self._model.add_var(name='ram')
      for idx, ram in enumerate(self._ram_availables()):
        self._model.add_constr(ram_var <= ram, name=f'ram_{idx}')
      cpu_var = self._model.add_var(name='cpu')
      for idx, cpu in enumerate(self._cpu_availables()):
        self._model.add_constr(cpu_var <= cpu, name=f'cpu_{idx}')
      storage_var = self._model.add_var(name='storage')
      for idx, storage in enumerate(self._storage_availables()):
        self._model.add_constr(storage_var <= storage, name=f'storage_{idx}')
      self._model.objective=maximize(ub_rp_var+lb_rp_var+ub_sp_var+lb_sp_var+dist_var+lat_var+ram_var+cpu_var+storage_var)

  def optimize(self) -> bool:
    if not self._optimized:
      opt_status = self._model.optimize()
      self._optimized = True
      if opt_status == OptimizationStatus.INFEASIBLE:
        print('Infeasible model!')
      elif opt_status == OptimizationStatus.OPTIMAL:
        print('Optimal solution found!')
      return opt_status in [OptimizationStatus.OPTIMAL, OptimizationStatus.UNBOUNDED, OptimizationStatus.FEASIBLE]
    else:
      print('Model already optimized!')
      return False

  def debug(self, debug_path: str = "DebugModel.lp"):
    self._model.write(debug_path)

  def get_solution_dict(self) -> dict[str, int]:
    if self._optimized:
      return {var.name: var.x for var in self._model.vars}
    else:
      return None

  def get_summarized_solution(self) -> list[str]:
    if self._optimized:
      return [var.name for var in list(filter(lambda x: x.x > 0.5 and x.name.startswith('z_'), self._model.vars))]
    else:
      return None

  def get_solution_dataframe(self) -> pd.DataFrame:
    if self._optimized:
      initial_info = [var.name for var in list(filter(lambda x: x.x > 0.5 and x.name.startswith('z_'), self._model.vars))]
      df_data = []
      for var in initial_info:
        __, request_name, node = var.split('_')
        df_data.append({"Request ID": request_name, "Requestor": self._requests[request_name]["node"], "Service": self._requests[request_name]["service"], "Deployment node": node})
      return pd.DataFrame(df_data)
    else:
      return None

