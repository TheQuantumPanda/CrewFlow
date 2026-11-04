class AppError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


class AuthError(AppError):
    pass


class TaskError(AppError):
    pass


class EmployeeError(AppError):
    pass


class AssignmentError(AppError):
    pass
