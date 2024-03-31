from typing import Literal, TypeAlias, TypedDict

fuckSony: TypeAlias = dict


class LimitPurseServiceOption(TypedDict):
    flag: bool
    upperLimit: int
    lowerLimit: int
    genNumber: int


class withMacOption(TypedDict):
    flag: bool


class Service(TypedDict):
    serviceCode: int
    serviceType: Literal["random", "cyclic", "purse"]
    isWithKey: bool
    access: Literal["read/write", "read", "direct", "cashback/decrement", "decrement"]

    overWrap: bool
    overWraptTarget: int

    serviceKey: str
    serviceKeyVersion: int

    serviceProperty: LimitPurseServiceOption | withMacOption


class Area(TypedDict):
    areaCode: int
    endServiceCode: str  # "fffe"
    canCreateChildArea: bool

    keyType: Literal["DES", "AES"]
    areaKey: str
    areaKeyVersion: int

    service: list[Service]

    areaProperty: fuckSony


class System(TypedDict):
    systemCode: str
    area: list[Area]
    systemProperty: fuckSony


class Card(TypedDict):
    IDm: str
    PMm: str
    system: list[System]
