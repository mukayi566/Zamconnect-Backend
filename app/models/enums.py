from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    REGISTRAR = "registrar"
    VERIFIER = "verifier"
    CITIZEN = "citizen"

class CitizenStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REJECTED = "rejected"

class AuditAction(str, Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    REGISTER_CITIZEN = "REGISTER_CITIZEN"
    UPDATE_CITIZEN = "UPDATE_CITIZEN"
    CHANGE_STATUS = "CHANGE_STATUS"
    VERIFY_NRC = "VERIFY_NRC"
    VERIFY_QR = "VERIFY_QR"
    REGENERATE_QR = "REGENERATE_QR"
    CREATE_ADMIN = "CREATE_ADMIN"
    DELETE_ADMIN = "DELETE_ADMIN"
    USSD_ACCESS = "USSD_ACCESS"
