from pybind11_project_conan.add_module import add

a = 1
b = 2
c = add(a, b)
print(f"{a} + {b} = {c}")
