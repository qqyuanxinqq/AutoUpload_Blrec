import hashlib
import rsa
import base64


def md5(data: str):
    """
    generate md5 hash of utf-8 encoded string.
    """
    return hashlib.md5(data.encode("utf-8")).hexdigest()


def md5_bytes(data: bytes):
    """
    generate md5 hash of binary.
    """
    return hashlib.md5(data).hexdigest()


def sign_str(data: str, app_secret: str):
    """
    sign a string of request parameters
    Args:
        data: string of request parameters, must be sorted by key before input.
        app_secret: a secret string coupled with app_key.

    Returns:
        A hash string. len=32
    """
    return md5(data + app_secret)


def sign_dict(data: dict, app_secret: str):
    """
    sign a dictionary of request parameters
    Args:
        data: dictionary of request parameters.
        app_secret: a secret string coupled with app_key.

    Returns:
        A hash string. len=32
    """
    data_str = []
    keys = list(data.keys())
    keys.sort()
    for key in keys:
        data_str.append("{}={}".format(key, data[key]))
    data_str = "&".join(data_str)
    data_str = data_str + app_secret
    return md5(data_str)


def encrypt_login_password(password, hash, pubkey):
    """
    encrypt password for login api.
    Args:
        password: plain text of user password.
        hash: hash provided by /api/oauth2/getKey.
        pubkey: public key provided by /api/oauth2/getKey.

    Returns:
        An encrypted cipher of password.
    """
    return base64.b64encode(rsa.encrypt(
        (hash + password).encode('utf-8'),
        rsa.PublicKey.load_pkcs1_openssl_pem(pubkey.encode()),
    ))

XOR_CODE = 23442827791579
MASK_CODE = 2251799813685247
MAX_AID = 1 << 51
ALPHABET = "FcwAPNKTMug3GV5Lj7EJnHpWsx4tb8haYeviqBz6rkCy12mUSDQX9RdoZf"
ENCODE_MAP = 8, 7, 0, 5, 1, 3, 2, 4, 6
DECODE_MAP = tuple(reversed(ENCODE_MAP))

BASE = len(ALPHABET)
PREFIX = "BV1"
PREFIX_LEN = len(PREFIX)
CODE_LEN = len(ENCODE_MAP)

def av2bv(aid: int) -> str:
    bvid = [""] * 9
    tmp = (MAX_AID | aid) ^ XOR_CODE
    for i in range(CODE_LEN):
        bvid[ENCODE_MAP[i]] = ALPHABET[tmp % BASE]
        tmp //= BASE
    return PREFIX + "".join(bvid)

def bv2av(bvid: str) -> int:
    assert bvid[:3] == PREFIX

    bvid = bvid[3:]
    tmp = 0
    for i in range(CODE_LEN):
        idx = ALPHABET.index(bvid[DECODE_MAP[i]])
        tmp = tmp * BASE + idx
    return (tmp & MASK_CODE) ^ XOR_CODE

assert av2bv(111298867365120) == "BV1L9Uoa9EUx"
assert bv2av("BV1L9Uoa9EUx") == 111298867365120