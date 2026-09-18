"""Imprime un par de claves RS256 listo para pegar en `.env` (saltos de línea como \n)."""

from app.core.keys import generate_rsa_keypair


def main() -> None:
    private_pem, public_pem = generate_rsa_keypair()
    print("JWT_PRIVATE_KEY=" + private_pem.strip().replace("\n", "\n"))
    print("JWT_PUBLIC_KEY=" + public_pem.strip().replace("\n", "\n"))


if __name__ == "__main__":
    main()
