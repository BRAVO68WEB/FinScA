from enum import StrEnum


class AccountType(StrEnum):
    SAVINGS = "savings"
    CURRENT = "current"
    CREDIT_CARD = "credit_card"
    WALLET = "wallet"
    UPI = "upi"
    LOAN = "loan"


class Channel(StrEnum):
    UPI = "upi"
    NEFT = "neft"
    IMPS = "imps"
    RTGS = "rtgs"
    DEBIT_CARD = "debit_card"
    CREDIT_CARD = "credit_card"
    ATM = "atm"
    CASH = "cash"
    CHEQUE = "cheque"
    NACH = "nach"
    OTHER = "other"


class Intent(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    SELF_TRANSFER = "self_transfer"
    EMI = "emi"
    LOAN_DISBURSAL = "loan_disbursal"
    REFUND = "refund"
    INVESTMENT = "investment"
    UNKNOWN = "unknown"


class SourceKind(StrEnum):
    PDF = "pdf"
    EMAIL = "email"
    SMS = "sms"


class MonthSource(StrEnum):
    STATEMENT = "statement"
    COMPUTED = "computed"


class LabelSource(StrEnum):
    RULE = "rule"
    TAXONOMY = "taxonomy"
    MODEL = "model"
    MANUAL = "manual"


class IncomeReview(StrEnum):
    PENDING = "pending"
    INCOME = "income"
    TRANSFER = "transfer"
    SKIPPED = "skipped"


class IngestStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class LoanStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


class EmiStatus(StrEnum):
    PAID = "paid"
    DUE = "due"
    MISSED = "missed"
    PARTIAL = "partial"


class GstSource(StrEnum):
    INVOICE = "invoice"
    INFERRED = "inferred"
    NONE = "none"


class Category(StrEnum):
    SALARY = "salary"
    FREELANCE = "freelance"
    BUSINESS_INCOME = "business_income"
    INTEREST = "interest"
    REFUND = "refund"
    GROCERY = "grocery"
    DINING = "dining"
    TRANSPORT = "transport"
    FUEL = "fuel"
    RENT = "rent"
    UTILITIES = "utilities"
    MOBILE_INTERNET = "mobile_internet"
    SHOPPING = "shopping"
    HEALTH = "health"
    EDUCATION = "education"
    ENTERTAINMENT = "entertainment"
    TRAVEL = "travel"
    INSURANCE = "insurance"
    INVESTMENT = "investment"
    TAX_GST = "tax_gst"
    EMI = "emi"
    TRANSFER = "transfer"
    SELF_TRANSFER = "self_transfer"
    CASH = "cash"
    OTHER = "other"
