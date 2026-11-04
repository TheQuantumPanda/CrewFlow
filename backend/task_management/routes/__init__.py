def register_routes(app):
    from .admin import admin_bp
    from .assignment import assignment_bp
    from .auth import auth_bp
    from .dashboard import dashboard_bp
    from .department import department_bp
    from .employee import employee_bp
    from .health import health_bp
    from .task import task_bp

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(task_bp, url_prefix="/api/tasks")
    app.register_blueprint(employee_bp, url_prefix="/api/employees")
    app.register_blueprint(department_bp, url_prefix="/api/departments")
    app.register_blueprint(assignment_bp, url_prefix="/api/assignments")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
