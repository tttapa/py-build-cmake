from __future__ import annotations


class ConfPath:
    def __init__(self, pth: tuple[str, ...] = ()):
        self.pth = pth

    @classmethod
    def from_string(cls, str_pth: str):
        return cls(tuple(filter(None, str_pth.split("/"))))

    def __str__(self):
        return "/".join(".." if x == "^" else x for x in self.pth)

    def join(self, suffix: str | ConfPath):
        if isinstance(suffix, str):
            suffix = ConfPath((suffix,))
        p1 = self.pth
        p2 = suffix.pth
        while p1 and p2 and p2[0] == "^":
            p1 = p1[:-1]
            p2 = p2[1:]
        return ConfPath(p1 + p2)

    def split(self) -> tuple[ConfPath, str]:
        return ConfPath(self.pth[:-1]), self.pth[-1]

    def split_front(self) -> tuple[str, ConfPath]:
        return self.pth[0], ConfPath(self.pth[1:])

    def __bool__(self):
        return bool(self.pth)
