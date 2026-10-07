"""Alignment settings use the ordinary profile config registry and loader."""


def test_alignment_config_is_registered_defaults_to_shadow_and_roundtrips(tmp_path, monkeypatch):
    from hermes_cli.config import _validate_config_key, load_config, save_config

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    for key in ("alignment_synthesis.mode", "alignment_synthesis.version"):
        assert _validate_config_key(key)[0]
    assert not _validate_config_key("alignment_synthesis.permission")[0]
    config = load_config()
    assert config["alignment_synthesis"]["mode"] == "shadow"
    assert not config["alignment_synthesis"]["version"]
    config["alignment_synthesis"] = {"mode": "active", "version": "a" * 64}
    save_config(config)
    assert load_config()["alignment_synthesis"] == config["alignment_synthesis"]
