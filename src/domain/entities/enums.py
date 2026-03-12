import enum


class HighlightTypeEnum(str, enum.Enum):
    WORD = "WORD"
    POST = "POST"


class SentimentsEnum(str, enum.Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class RoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    DEV = "DEV"
    USER = "USER"
    ANALYST = "ANALYST"


class SocialNetworkEnum(str, enum.Enum):
    FACEBOOK = "FACEBOOK"
    INSTAGRAM = "INSTAGRAM"
    X = "X"
    TIKTOK = "TIKTOK"
    YOUTUBE = "YOUTUBE"
    TELEGRAM = "TELEGRAM"
    ALL = "ALL"


class PostTypeEnum(str, enum.Enum):
    GOV = "GOV"
    PRESS = "PRESS"
    DEFAULT = "DEFAULT"


class HighlightStatusEnum(str, enum.Enum):
    PUBLISHED = "PUBLISHED"
    DRAFT = "DRAFT"
    ARQUIVED = "ARQUIVED"


class StopTypeEnum(str, enum.Enum):
    WORD = "WORD"
    HASHTAG = "HASHTAG"
    USER = "USER"
    RANKING = "RANKING"


class StatusReportEnum(str, enum.Enum):
    INIT = "INIT"
    PROCESSING = "PROCESSING"
    CONCLUDED = "CONCLUDED"
    ERROR = "ERROR"


class ReportCriticsEnum(str, enum.Enum):
    NON_CRITICAL = "NON_CRITICAL"
    CRITICAL_GOV = "CRITICAL_GOV"
    CRITICAL_COP = "CRITICAL_COP"
    NEGATIONISM = "NEGATIONISM"


class TermTypeEnum(str, enum.Enum):
    CHANNEL = "CHANNEL"
    TERM = "TERM"