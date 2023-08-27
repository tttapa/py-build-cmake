from pybind11_project.add_module import add

a = 1
b = 2
c = add(a, b)
print(f'{a} + {b} = {c}')
