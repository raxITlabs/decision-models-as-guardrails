"""Where the edition 2 runners read rows from (goldrails_bench.e2_source): the pinned Hub copy by default, the staged
folder until the owner fills in the revision, the build with --source local. No network: the Hub path is exercised
on the staged folder, which has the Hub layout."""
import pytest

from goldrails_bench import e2_source as S


def test_default_is_the_staged_folder_until_the_revision_is_set(monkeypatch):
    monkeypatch.delenv(S.ENV, raising=False)
    monkeypatch.setattr(S, "E2_HF_REVISION", None)
    assert S.source() == "dataset/publish/release-1.0.0"
    monkeypatch.setattr(S, "E2_HF_REVISION", "a" * 40)
    assert S.source() == f"hf:{S.HF_REPO}@{'a' * 40}"
    monkeypatch.setenv(S.ENV, "local")
    assert S.source() == "local" and S.dataset_dir() == S.BUILD
    assert S.source("dataset/edition2/build") == "dataset/edition2/build"


def test_a_hub_source_must_be_pinned():
    with pytest.raises(ValueError, match="pin a revision"):
        S._hub_folder(S.HF_REPO)


def test_a_missing_explicit_source_raises(tmp_path, monkeypatch):
    monkeypatch.delenv(S.ENV, raising=False)
    with pytest.raises(S.E2SourceMissing):
        S.dataset_dir(str(tmp_path / "nowhere"))
    with pytest.raises(S.E2SourceMissing):
        S.dev_files(str(tmp_path / "nowhere"))


def test_a_missing_default_source_falls_back_to_the_build_for_dev_rows(tmp_path, monkeypatch):
    monkeypatch.delenv(S.ENV, raising=False)
    monkeypatch.setattr(S, "E2_HF_REVISION", None)
    monkeypatch.setattr(S, "STAGED", tmp_path / "not-staged")
    monkeypatch.setattr(S, "default_source", lambda: str(tmp_path / "not-staged"))
    with pytest.warns(UserWarning):
        assert S.dev_files() == sorted(S.BUILD.glob("F*.dev.jsonl"))


def test_a_build_layout_directory_is_used_as_it_is(tmp_path):
    (tmp_path / "F1.dev.jsonl").write_text("")
    assert S.dataset_dir(str(tmp_path)) == tmp_path


@pytest.mark.skipif(not ((S.STAGED / "canonical.json").exists() and (S.BUILD / "manifest.json").exists()),
                    reason="the staged folder or the edition 2 build is not on this machine")
def test_the_staged_copy_materializes_byte_identical_to_the_build(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "CACHE", tmp_path / "cache")
    d = S.dataset_dir(str(S.STAGED))
    assert d.is_relative_to(tmp_path)
    names = sorted(p.relative_to(S.BUILD) for p in S.BUILD.glob("F*.jsonl")) + \
        sorted(p.relative_to(S.BUILD) for p in (S.BUILD / "private").glob("F*.jsonl"))
    assert names
    for n in names:
        assert (d / n).read_bytes() == (S.BUILD / n).read_bytes(), n
    stamp = (d / "stamp.json").read_text()
    assert S.dataset_dir(str(S.STAGED)) == d and (d / "stamp.json").read_text() == stamp   # cached, not rebuilt
