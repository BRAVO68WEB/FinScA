from __future__ import annotations

from pathlib import Path

from finsca.config.passwords import PasswordEntry, add_password, candidates_for, load_store, mask


def test_store_roundtrip_and_filename_match(tmp_path: Path) -> None:
    dest = tmp_path / "pdf_passwords.yaml"
    add_password("01011990", match="hdfc", path=dest)
    add_password("GLOBAL", path=dest)
    add_password("icicipan", match="icici", path=dest)
    entries = load_store(dest)
    assert entries == [
        PasswordEntry("01011990", "hdfc"),
        PasswordEntry("GLOBAL", None),
        PasswordEntry("icicipan", "icici"),
    ]
    hdfc = candidates_for("HDFC_CC_1234.pdf", entries, extra="ENV")
    assert hdfc[0] == "01011990"
    assert hdfc[1:] == ["GLOBAL", "icicipan", "ENV"]
    other = candidates_for("unknown.pdf", entries)
    assert other == ["01011990", "GLOBAL", "icicipan"]


def test_yaml_yes_match_is_not_bool(tmp_path: Path) -> None:
    dest = tmp_path / "pdf_passwords.yaml"
    dest.write_text('passwords:\n  - password: "27032003"\n    match: yes\n', encoding="utf-8")
    entries = load_store(dest)
    assert entries[0].match == "yes"
    assert candidates_for("estatement_yes.bank.in.pdf", entries) == ["27032003"]


def test_mask_hides_prefix() -> None:
    assert mask("01011990") == "******90"
    assert mask("ab") == "**"
