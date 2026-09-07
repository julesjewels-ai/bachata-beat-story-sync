with open("tests/unit/test_phase_manager.py", "r") as f:
    c = f.read()
c = c.replace('selection: str = "rotate",', 'selection: Literal["rotate", "random", "fixed"] = "rotate",')
with open("tests/unit/test_phase_manager.py", "w") as f:
    f.write(c)
