from databases import Database
from fastapi import Request
from fastapi.datastructures import State


class CState(State):
    def __init__(self):
        super().__init__()

    @property
    def database(self) -> Database: ...


class CRequest(Request):
    def __init__(self):
        super().__init__()
        self.state: CState = CState()
