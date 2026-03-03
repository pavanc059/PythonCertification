# Example 01
name: str = "Guido"
pi: float = 3.142
centered: bool = False

# Example 02
names: list = ["Guido", "Thomas", "Bobby"]
version: tuple = (3, 7, 1)
options: dict = {"centered": False, "capitalize": True}

type(names[2])

__annotations__

# Example 03
from typing import Dict, List, Tuple

names: List[str] = ["Guido", "Thomas", "Bobby"]
version: Tuple[int, int, int] = (3, 7, 1)
options: Dict[str, bool] = {"centered": False, "capitalize": True}

__annotations__