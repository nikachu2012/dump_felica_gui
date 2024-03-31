from math import atan
from typing import Literal, TypeAlias

import nfc
from numpy import append

SystemCode: TypeAlias = bytearray
IDm: TypeAlias = bytes
PMm: TypeAlias = bytes
RequestData: TypeAlias = bytes | None

serviceCode: TypeAlias = bytes | None
areaCode: TypeAlias = bytes | None
endServiceCode: TypeAlias = bytes | None

SF1: TypeAlias = int
SF2: TypeAlias = int


def conv_bytes_to_str(input: bytes) -> str:
    result = ""
    for i in input:
        if 0x20 <= i <= 0x7E:
            result += chr(i)
        else:
            result += "."
    return result


def service_to_str(service: int):
    if service == 1:
        return "Random "
    elif service == 2:
        return "Cyclic "
    elif service == 3:
        return "Purse "
    else:
        return ""


def access_to_str(access: int, with_encryption: bool):
    result = ""

    if access == 1:
        result += "r/w"
    elif access == 2:
        result += "read"
    elif access == 3:
        result += "direct"
    elif access == 4:
        result += "cashback / decrement"
    elif access == 5:
        result += "decrement"
    elif access == 6:
        result += "read"
    else:
        result += "undefined"

    result += " with key" if with_encryption else " w/o key"
    return result


def get_ic_type(ic_type: int) -> str:
    switcher = {
        0x01: "RC-S915",
        0x06: "FeliCa Mobile 1.0",
        0x07: "FeliCa Mobile 1.0",
        0x08: "RC-S952",
        0x09: "RC-S953",
        0x0B: "Felica Standard (Suica(DES))",
        0x0D: "RC-S960",
        0x10: "FeliCa Mobile 2.0",
        0x11: "FeliCa Mobile 2.0",
        0x12: "FeliCa Mobile 2.0",
        0x13: "FeliCa Mobile 2.0",
        0x14: "FeliCa Mobile 3.0",
        0x15: "FeliCa Mobile 3.0",
        0x17: "FeliCa Mobile 4.0",
        0x18: "FeliCa Mobile 4.1",
        0x19: "FeliCa Mobile 4.1",
        0x1A: "FeliCa Mobile 4.1",
        0x1B: "FeliCa Mobile 4.1",
        0x1C: "FeliCa Mobile 4.1",
        0x1D: "FeliCa Mobile 4.1",
        0x1E: "FeliCa Mobile 4.1",
        0x1F: "FeliCa Mobile 4.1",
        0x20: "RC-S962",
        0x31: "FeliCa Standard (Suica)",
        0x32: "RC-SA00/1",
        0x36: "FeliCa Standard",
        0x44: "RC-SA20/1",
        0x45: "RC-SA20/2",
        0xF1: "RC-S966 (FeliCa Lite-S)",
        0xF0: "RC-S965 (FeliCa Lite)",
        0xF2: "RC-S967 (FeliCa Link Lite-S / Lite-S HT mode)",
        0xE1: "RC-S967 (FeliCa Link Plug mode)",
        0xFF: "RC-S967 (FeliCa Link NFC-DEP mode)",
        0xE0: "RC-S926 (FeliCa Plug)",
        0xFE: "Host-based Card Emulation for NFC-F",
    }
    return switcher.get(ic_type, "FeliCa card")


liteSBlockList: list[int] = [
    0x00,
    0x01,
    0x02,
    0x03,
    0x04,
    0x05,
    0x06,
    0x07,
    0x08,
    0x09,
    0x0A,
    0x0B,
    0x0C,
    0x0D,
    0x0E,
    0x80,
    0x82,
    0x83,
    0x84,
    0x85,
    0x86,
    0x87,
    0x88,
    0x90,
    0x91,
    0x92,
    0xA0,
]


def parse_service_code(service_code: bytes) -> tuple[int, int, bool]:
    """
    service
    0: エラー
    1: ランダムサービス
    2: サイクリックサービス
    3: パースサービス

    access
    0: エラー
    1: リード／ライトアクセス
    2: リードオンリーアクセス

    3: ダイレクトアクセス
    4: キャッシュバック／デクリメントアクセス
    5: デクリメントアクセス
    6: リードオンリーアクセス

    withEncryption
    false: 認証不要
    true : 認証必要
    """
    service_attribute = service_code[1] & 0x3F

    service = 0
    access = 0
    with_encryption = False

    service_attribute_shifted = (service_attribute & 0x3C) >> 2
    if service_attribute_shifted == 2:
        service = 1
    elif service_attribute_shifted == 3:
        service = 2
    elif service_attribute_shifted in (4, 5):
        service = 3

    with_encryption = (service_attribute & 0x1) == 0

    if (service_attribute & 0x10) == 0x10:
        # Purse Service
        access = ((service_attribute & 0x07) // 2) + 3
    else:
        access = 2 if (service_attribute & 0x2) == 0x2 else 1

    return service, access, with_encryption


def commandSender(clf, command: bytes) -> bytearray:
    print("<<", command.hex())
    temp = clf.exchange(command, timeout=1)

    if temp is None:
        raise Exception("Target has not answer.")

    else:
        print(">>", temp.hex())
        return temp


def lenCalc(packet: bytes) -> bytes:
    return (len(packet) + 1).to_bytes() + packet


def polling(
    clf,
    targetSystem: SystemCode,
    requestCode: Literal[0x00, 0x01, 0x02] = 0x00,
    timeSlot: Literal[0x00, 0x01, 0x03, 0x07, 0x0F] = 0x0F,
) -> tuple[IDm, PMm, RequestData]:
    """
    return:
        tuple[
            IDm: bytes (len:8)
            PMm: bytes (len:8)
            RequestData: bytes | None (len:2)
        ]
    """
    packet = int(0x00).to_bytes() + targetSystem + requestCode.to_bytes() + timeSlot.to_bytes()
    response = commandSender(clf, lenCalc(packet))

    idm: bytes = response[2 : 2 + 8]
    pmm: bytes = response[10 : 10 + 8]

    # Le 0x01 IDm(x8) PMm(x8) RequestData(x2)
    if len(response) > 18:
        request_data: bytes | None = response[10 + 8 : 10 + 10]
    else:
        request_data: bytes | None = None

    return (idm, pmm, request_data)


def requestSystemCode(clf, idm: bytes) -> list[bytearray]:
    """
    return: List[System Code...]
    """
    packet = int(0x0C).to_bytes() + idm
    response = commandSender(clf, lenCalc(packet))

    result = []
    # Le 0x0D IDm(x8) Le List
    for i in range(response[10]):
        result.append(response[11 + 2 * i : 11 + 2 * i + 2])

    return result


def searchServiceCode(clf, idm: bytes, count: int) -> tuple[serviceCode, areaCode, endServiceCode]:
    """
    Argument:
        clf -> ContactlessFrontend
        IDm -> IDm(bytes)
        count -> 0x0000 (uint16)
    return:
        serviceCode -> bytes (big endian) | None
        areaCode -> bytes (big endian) | None
        endServiceCode -> bytes (big endian) | None
    """

    packet = int(0x0A).to_bytes() + idm + count.to_bytes(2, "little")
    response = commandSender(clf, lenCalc(packet))

    if len(response) == 12:
        return (response[10:12][::-1], None, None)
    else:
        return (None, response[10:12][::-1], response[12:14][::-1])


def readWoEnc(clf, idm: bytes, service: bytes, block: int) -> tuple[SF1, SF2, bytes | None]:
    """
    Argument:
        clf -> ContactlessFrontend
        IDm -> IDm(bytes)
        count -> service Big endian (b"\\x09\\x0f")

    """
    blocklist: bytes = b""
    if block <= 0xFF:
        blocklist += b"\x80" + block.to_bytes()
    else:
        blocklist += b"\x00" + block.to_bytes(2, "little")

    packet = b"\x06" + idm + b"\x01" + service[::-1] + b"\01" + blocklist
    response = commandSender(clf, lenCalc(packet))

    if response[10] == 0x00 and response[11] == 0x00:
        return (response[10], response[11], response[11:])
    else:
        return (response[10], response[11], None)


def readWoEncOneService(clf, idm: bytes, service: bytes) -> list[bytes]:
    result: list[bytes] = []
    count = 0
    while True:
        SF1, SF2, data = readWoEnc(clf, idm, service, count)

        if SF1 == 0x00 and SF2 == 0x00 and data:
            result.append(data)
        else:
            break

        count += 1

    return result
