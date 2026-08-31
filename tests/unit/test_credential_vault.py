import pytest

from crossborder_api.credential_vault import CredentialDecryptionError, CredentialVault


def test_credential_vault_encrypts_without_plaintext_and_round_trips() -> None:
    vault = CredentialVault("a-test-signing-secret-with-enough-entropy")
    credentials = {"access_token": "secret-token", "app_secret": "secret-app-key"}

    encrypted = vault.encrypt(credentials)

    assert "secret-token" not in encrypted
    assert "secret-app-key" not in encrypted
    assert vault.decrypt(encrypted) == credentials


def test_credential_vault_rejects_ciphertext_from_another_key() -> None:
    encrypted = CredentialVault("first-key").encrypt({"access_token": "token"})

    with pytest.raises(CredentialDecryptionError):
        CredentialVault("second-key").decrypt(encrypted)
