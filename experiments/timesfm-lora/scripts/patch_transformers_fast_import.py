from __future__ import annotations

from pathlib import Path


ROOT_START = "    _import_structure = {k: set(v) for k, v in _import_structure.items()}\n\n"
ROOT_START += '    import_structure = define_import_structure(Path(__file__).parent / "models", prefix="models")\n'
ROOT_START += "    import_structure[frozenset({})].update(_import_structure)\n"

ROOT_REPLACEMENT = "    _import_structure = {k: set(v) for k, v in _import_structure.items()}\n\n"
ROOT_REPLACEMENT += "    import_structure = {frozenset({}): _import_structure}\n"
ROOT_REPLACEMENT += '    import_structure[frozenset({})]["models.auto.modeling_auto"] = {\n'
ROOT_REPLACEMENT += '        "AutoModel",\n'
ROOT_REPLACEMENT += '        "AutoModelForCausalLM",\n'
ROOT_REPLACEMENT += '        "AutoModelForQuestionAnswering",\n'
ROOT_REPLACEMENT += '        "AutoModelForSeq2SeqLM",\n'
ROOT_REPLACEMENT += '        "AutoModelForSequenceClassification",\n'
ROOT_REPLACEMENT += '        "AutoModelForTokenClassification",\n'
ROOT_REPLACEMENT += "    }\n"
ROOT_REPLACEMENT += '    import_structure[frozenset({})]["models.auto.configuration_auto"] = {\n'
ROOT_REPLACEMENT += '        "AutoConfig",\n'
ROOT_REPLACEMENT += "    }\n"
ROOT_REPLACEMENT += '    import_structure[frozenset({})]["models.auto.tokenization_auto"] = {\n'
ROOT_REPLACEMENT += '        "AutoTokenizer",\n'
ROOT_REPLACEMENT += "    }\n"
ROOT_REPLACEMENT += '    import_structure[frozenset({})]["models.bloom.modeling_bloom"] = {\n'
ROOT_REPLACEMENT += '        "BloomPreTrainedModel",\n'
ROOT_REPLACEMENT += "    }\n"
ROOT_REPLACEMENT += '    import_structure[frozenset({})]["models.timesfm2_5.configuration_timesfm2_5"] = {\n'
ROOT_REPLACEMENT += '        "TimesFm2_5Config",\n'
ROOT_REPLACEMENT += "    }\n"
ROOT_REPLACEMENT += '    import_structure[frozenset({})]["models.timesfm2_5.modeling_timesfm2_5"] = {\n'
ROOT_REPLACEMENT += '        "TimesFm2_5Model",\n'
ROOT_REPLACEMENT += '        "TimesFm2_5ModelForPrediction",\n'
ROOT_REPLACEMENT += '        "TimesFm2_5PreTrainedModel",\n'
ROOT_REPLACEMENT += "    }\n"

MODELS_START = '    sys.modules[__name__] = _LazyModule(__name__, _file, define_import_structure(_file), module_spec=__spec__)\n'

MODELS_REPLACEMENT = "    import_structure = {\n"
MODELS_REPLACEMENT += "        frozenset({}): {\n"
MODELS_REPLACEMENT += '            "auto.modeling_auto": {\n'
MODELS_REPLACEMENT += '                "AutoModel",\n'
MODELS_REPLACEMENT += '                "AutoModelForCausalLM",\n'
MODELS_REPLACEMENT += '                "AutoModelForQuestionAnswering",\n'
MODELS_REPLACEMENT += '                "AutoModelForSeq2SeqLM",\n'
MODELS_REPLACEMENT += '                "AutoModelForSequenceClassification",\n'
MODELS_REPLACEMENT += '                "AutoModelForTokenClassification",\n'
MODELS_REPLACEMENT += "            },\n"
MODELS_REPLACEMENT += '            "auto.tokenization_auto": {"AutoTokenizer"},\n'
MODELS_REPLACEMENT += '            "auto.configuration_auto": {"AutoConfig"},\n'
MODELS_REPLACEMENT += '            "bloom.modeling_bloom": {"BloomPreTrainedModel"},\n'
MODELS_REPLACEMENT += '            "timesfm2_5.configuration_timesfm2_5": {"TimesFm2_5Config"},\n'
MODELS_REPLACEMENT += '            "timesfm2_5.modeling_timesfm2_5": {\n'
MODELS_REPLACEMENT += '                "TimesFm2_5Model",\n'
MODELS_REPLACEMENT += '                "TimesFm2_5ModelForPrediction",\n'
MODELS_REPLACEMENT += '                "TimesFm2_5PreTrainedModel",\n'
MODELS_REPLACEMENT += "            },\n"
MODELS_REPLACEMENT += "        }\n"
MODELS_REPLACEMENT += "    }\n"
MODELS_REPLACEMENT += "    sys.modules[__name__] = _LazyModule(__name__, _file, import_structure, module_spec=__spec__)\n"

AUTO_START = '    sys.modules[__name__] = _LazyModule(__name__, _file, define_import_structure(_file), module_spec=__spec__)\n'

AUTO_REPLACEMENT = "    import_structure = {\n"
AUTO_REPLACEMENT += "        frozenset({}): {\n"
AUTO_REPLACEMENT += '            "modeling_auto": {\n'
AUTO_REPLACEMENT += '                "AutoModel",\n'
AUTO_REPLACEMENT += '                "AutoModelForCausalLM",\n'
AUTO_REPLACEMENT += '                "AutoModelForQuestionAnswering",\n'
AUTO_REPLACEMENT += '                "AutoModelForSeq2SeqLM",\n'
AUTO_REPLACEMENT += '                "AutoModelForSequenceClassification",\n'
AUTO_REPLACEMENT += '                "AutoModelForTokenClassification",\n'
AUTO_REPLACEMENT += "            },\n"
AUTO_REPLACEMENT += '            "tokenization_auto": {"AutoTokenizer"},\n'
AUTO_REPLACEMENT += '            "configuration_auto": {"AutoConfig"},\n'
AUTO_REPLACEMENT += "        }\n"
AUTO_REPLACEMENT += "    }\n"
AUTO_REPLACEMENT += "    sys.modules[__name__] = _LazyModule(__name__, _file, import_structure, module_spec=__spec__)\n"


def patch_file(path: Path, start: str, replacement: str) -> None:
    text = path.read_text()
    if replacement in text:
        print(f"[patch] already patched {path}")
        return
    if start not in text:
        raise SystemExit(f"expected import block was not found in {path}")

    path.write_text(text.replace(start, replacement))
    print(f"[patch] patched {path}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    candidates = list(root.glob(".venv/lib/python*/site-packages/transformers/__init__.py"))
    if not candidates:
        raise SystemExit("transformers __init__.py not found under .venv")

    root_init = candidates[0]
    models_init = root_init.parent / "models" / "__init__.py"
    auto_init = root_init.parent / "models" / "auto" / "__init__.py"
    patch_file(root_init, ROOT_START, ROOT_REPLACEMENT)
    patch_file(models_init, MODELS_START, MODELS_REPLACEMENT)
    patch_file(auto_init, AUTO_START, AUTO_REPLACEMENT)


if __name__ == "__main__":
    main()
