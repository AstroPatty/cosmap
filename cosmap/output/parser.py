from abc import ABC, abstractmethod
import numpy as np
import pandas as pd

class cosmapOutputParser(ABC):

    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def __call__(self, *args, **kwargs):
        pass


class weightsOutputParser(cosmapOutputParser):
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, output, *args, **kwargs):
        center = output['center']
        field_weights = output['field_weights']
        control_weights = output['control_weights']
        np.seterr(invalid='raise')
        return_vals = {'ra': center.ra, 'dec': center.dec}

        for weight_name, weight_values in field_weights.items():
            try:
                control_weight = float(control_weights[weight_name])
            except:
                control_weight = np.sum(control_weights[weight_name])

            try:
                field_weight = float(weight_values)
            except:
                field_weight = np.sum(weight_values)

            try:
                ratio = field_weight/control_weight
            except:
                ratio = -1
            return_vals[weight_name] = [ratio]

        return pd.DataFrame(return_vals, columns=return_vals.keys())
