from ..extensions import db


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))

    employees = db.relationship("Employee", back_populates="department")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "description": self.description}
