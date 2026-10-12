class ProjectError(Exception):
    def __init__(self, code: str, status: int = 400):
        self.code, self.status = "errors." + code, status
        super().__init__(self.code)
