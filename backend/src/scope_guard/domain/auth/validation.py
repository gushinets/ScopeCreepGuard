import re

JS_SPACE = r"\x09-\x0d\x20\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
EMAIL = re.compile(rf"^[^{JS_SPACE}@]+@[^{JS_SPACE}@]+\.[^{JS_SPACE}@]+$")


class AuthError(Exception):
    def __init__(self, code: str, status: int):
        self.code, self.status = code, status
        super().__init__(code)


def credentials(body: dict) -> tuple[str, str]:
    if not isinstance(body.get("email"), str):
        raise AuthError("errors.emailRequired", 400)
    if not isinstance(body.get("password"), str):
        raise AuthError("errors.passwordRequired", 400)
    email = re.sub(rf"^[{JS_SPACE}]+|[{JS_SPACE}]+$", "", body["email"]).lower()
    password = body["password"]
    if not EMAIL.fullmatch(email):
        raise AuthError("errors.invalidEmail", 400)
    if len(password.encode("utf-16-le", errors="surrogatepass")) // 2 < 8:
        raise AuthError("errors.passwordTooShort", 400)
    return email, password
