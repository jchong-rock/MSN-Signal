from dataclasses import dataclass, astuple


@dataclass
class ListNumbers():

    FORWARD_LIST: str = "FL"
    ALLOW_LIST: str = "AL"
    BLOCK_LIST: str = "BL"
    REVERSE_LIST: str = "RL"

    def __iter__(self):
        return iter((astuple(self)))