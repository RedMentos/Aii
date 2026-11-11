"""Bounded, source-approved numeric A3 teacher/student projector experiment.

Pure Python synthetic prototype, NOT full A3 modality integration, JEPA, or Android proof.
"""
import json
import math
import os
from pathlib import Path

class A3Projector:
    def __init__(self, inputs=3, outputs=2, learning_rate=.02):
        if type(inputs) is not int or type(outputs) is not int or not 1 <= inputs <= 64 or not 1 <= outputs <= 64:
            raise ValueError("invalid dimensions")
        if type(learning_rate) not in (float, int) or not math.isfinite(learning_rate) or not 0 < learning_rate <= .1:
            raise ValueError("invalid learning rate")
        self.inputs, self.outputs, self.lr = inputs, outputs, float(learning_rate)
        self.weights = [[0.0]*inputs for _ in range(outputs)]
        self.bias = [0.0]*outputs
        self.steps = 0

    def _vector(self, values, n):
        if not isinstance(values, (list, tuple)) or len(values) != n or any(type(v) not in (float,int) or not math.isfinite(v) or abs(v)>100 for v in values):
            raise ValueError("finite bounded vector required")
        return [float(v) for v in values]

    def predict(self, features):
        x = self._vector(features, self.inputs)
        return [sum(w*v for w,v in zip(row,x))+b for row,b in zip(self.weights,self.bias)]

    def train(self, features, teacher, *, trusted=False):
        if trusted is not True:
            raise PermissionError("verified teacher approval required")
        x = self._vector(features,self.inputs)
        y = self._vector(teacher,self.outputs)
        errors = [p-t for p,t in zip(self.predict(x),y)]
        loss = sum(e*e for e in errors)/self.outputs
        for j,e in enumerate(errors):
            gradient = max(-1.0,min(1.0,2*e/self.outputs))
            self.weights[j] = [w-self.lr*gradient*v for w,v in zip(self.weights[j],x)]
            self.bias[j] -= self.lr*gradient
        self.steps += 1
        return loss

    def save(self, path):
        dest = Path(path)
        data = {"schema":1,"inputs":self.inputs,"outputs":self.outputs,"lr":self.lr,"steps":self.steps,"weights":self.weights,"bias":self.bias}
        tmp = dest.with_name(dest.name+".tmp")
        with tmp.open("w",encoding="utf-8") as f:
            json.dump(data,f,allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp,dest)

    @classmethod
    def load(cls,path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("schema") != 1 or type(data.get("steps")) is not int or not 0 <= data["steps"] <= 100000000:
            raise ValueError("invalid checkpoint")
        p = cls(data["inputs"],data["outputs"],data["lr"])
        if not isinstance(data.get("weights"),list) or len(data["weights"]) != p.outputs:
            raise ValueError("invalid weights")
        p.weights = [p._vector(row,p.inputs) for row in data["weights"]]
        p.bias = p._vector(data["bias"],p.outputs)
        p.steps = data["steps"]
        return p
