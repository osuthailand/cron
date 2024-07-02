from databases import Database
from fastapi import Request
from fastapi.datastructures import State


class CState(State):
    def __init__(self):
        super().__init__()
        self.database: Database


class CRequest(Request):
    def __init__(self, *args):
        super().__init__(*args)
        self.state: CState = CState()
