# models/user.py
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class Role(db.Model):
    """Defines the roles available in the system (admin, faculty, student, etc.)."""

    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    users = db.relationship("User", back_populates="role", lazy="dynamic")
    role_permissions = db.relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )

    @property
    def name(self):
        return self.role_name.lower() if self.role_name else ""

    def __repr__(self):
        return f"<Role id={self.id} role_name='{self.role_name}'>"

    def to_dict(self):
        return {
            "id": self.id,
            "role_name": self.role_name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Permission(db.Model):
    """Granular permissions that can be assigned to roles."""

    __tablename__ = "permissions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    permission_name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(50), nullable=True)  # e.g. "attendance", "exam"
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    role_permissions = db.relationship(
        "RolePermission", back_populates="permission", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Permission id={self.id} permission_name='{self.permission_name}'>"

    def to_dict(self):
        return {
            "id": self.id,
            "permission_name": self.permission_name,
            "description": self.description,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RolePermission(db.Model):
    """Association table between Role and Permission (many-to-many)."""

    __tablename__ = "role_permissions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_id = db.Column(
        db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_id = db.Column(
        db.Integer, db.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    role = db.relationship("Role", back_populates="role_permissions")
    permission = db.relationship("Permission", back_populates="role_permissions")

    __table_args__ = (
        db.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    def __repr__(self):
        return f"<RolePermission role_id={self.role_id} permission_id={self.permission_id}>"


class User(db.Model, UserMixin):
    """Core user account shared across all roles (admin, faculty, student)."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)

    role_id = db.Column(
        db.Integer, db.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    profile_photo_key = db.Column(db.String(512), nullable=True)  # S3 object key

    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    role = db.relationship("Role", back_populates="users")
    student_profile = db.relationship(
        "Student", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    faculty_profile = db.relationship(
        "Faculty", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    sent_notifications = db.relationship(
        "Notification",
        foreign_keys="Notification.sender_id",
        back_populates="sender",
        lazy="dynamic",
    )
    targeted_notifications = db.relationship(
        "Notification",
        foreign_keys="Notification.target_user_id",
        back_populates="target_user",
        lazy="dynamic",
    )
    audit_logs = db.relationship("AuditLog", back_populates="user", lazy="dynamic")

    __table_args__ = (
        db.Index("ix_users_email", "email"),
        db.Index("ix_users_username", "username"),
    )

    # ------------------------------------------------------------------
    # Password helpers
    # ------------------------------------------------------------------

    def set_password(self, password: str) -> None:
        """Hash and store *password*."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return True if *password* matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def get_full_name(self) -> str:
        """Return '<first_name> <last_name>'."""
        return f"{self.first_name} {self.last_name}".strip()

    def get_permissions(self) -> list[str]:
        """Return a list of permission_name strings for this user's role."""
        if not self.role:
            return []
        return [
            rp.permission.permission_name
            for rp in self.role.role_permissions
            if rp.permission
        ]

    def has_permission(self, permission_name: str) -> bool:
        """Return True if this user's role grants *permission_name*."""
        return permission_name in self.get_permissions()

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialize the user to a dictionary (password hash excluded)."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role.to_dict() if self.role else None,
            "is_active": self.is_active,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.get_full_name(),
            "phone": self.phone,
            "profile_photo_key": self.profile_photo_key,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<User id={self.id} username='{self.username}' role_id={self.role_id}>"
