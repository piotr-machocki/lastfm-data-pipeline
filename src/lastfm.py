import hashlib


def sign_request(params: dict, secret: str) -> str:
    signature_string = "".join(
        f"{key}{params[key]}"
        for key in sorted(params)
    )

    signature_string += secret

    return hashlib.md5(signature_string.encode("utf-8")).hexdigest()