from sys import path

path.append('d:\\workspace\\learning\\Python_projects\\Python\\PythonCertification\\ch_06_Modules_packages\\learning\\packages')

import extra.iota
import extra.good.best.sigma
from extra.good.best.tau import funT


print(extra.iota.funI())
print(extra.good.best.sigma.funS())
print(funT())