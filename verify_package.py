"""仅检查封装、哈希、语法和必要导入；不运行科学模型或求解器。"""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-imports', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'MANIFEST.json').read_text(encoding='utf-8'))
    observed = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()
                and p.relative_to(ROOT).parts[0] != 'outputs'
                and '__pycache__' not in p.parts and '.git' not in p.parts}
    assert observed == set(manifest) | {'MANIFEST.json'}, '附件文件清单不一致'
    for name, expected in manifest.items():
        item = ROOT / name
        assert hashlib.sha256(item.read_bytes()).hexdigest() == expected, name
    for name in ('reproduce.py', 'src/kernel.py', 'verify_package.py'):
        text = (ROOT / name).read_text(encoding='utf-8')
        ast.parse(text, filename=name)
        compile(text, name, 'exec')  # 只编译到内存，不执行或创建缓存。
    frozen = json.loads((ROOT / 'frozen-inputs.json').read_text(encoding='utf-8'))
    assert all(manifest[name] == value for name, value in frozen.items())
    summary = json.loads((ROOT / 'prior-verification/run-summary.json').read_text(encoding='utf-8'))
    assert summary['status'] == 'PASS_ONE_WINDOW_ONLY'
    assert summary['optimizer_calls_entered'] == 4
    assert summary['reproduced_cases_verified'] == 4
    versions = {}
    mismatches = {}
    import_failures = {}
    arrays = {}
    if args.check_imports:
        expected_versions = {'numpy': '2.3.5', 'pandas': '3.0.1', 'scipy': '1.16.2'}
        for name, expected in expected_versions.items():
            try:
                module = importlib.import_module(name)
                versions[name] = module.__version__
                if versions[name] != expected:
                    mismatches[name] = {'expected': expected, 'observed': versions[name]}
            except ImportError as error:
                # 导入缺失如实保留；包结构通过不能冒称运行环境已齐。
                import_failures[name] = {'type': type(error).__name__, 'message': str(error)}
        np = importlib.import_module('numpy')
        for item in sorted((ROOT / 'data/input').glob('*.npz')):
            with np.load(item, allow_pickle=False) as archive:
                arrays[item.name] = {key: {'shape': list(archive[key].shape),
                                         'dtype': str(archive[key].dtype)}
                                     for key in archive.files}
                assert all(archive[key].dtype.kind in 'iufb' for key in archive.files)
                assert all(np.isfinite(archive[key]).all() for key in archive.files)
                if item.name == 'input.npz':
                    assert archive['qref'].shape == (168, 4)
                    assert archive['observed'].shape == (168, 4)
                    assert archive['timestamp_ns'].shape == (168,)
                elif item.name == 'price.npz':
                    assert archive.files == ['price_CNY_per_MWh']
                    assert archive['price_CNY_per_MWh'].shape == (168,)
                else:
                    assert archive['q'].shape == (168, 4)
    report = {'status': 'PASS_PACKAGING_ONLY', 'manifest_files_checked': len(manifest),
              'scientific_model_calls_this_check': 0, 'optimizer_calls_this_check': 0,
              'versions': versions, 'prior_environment_version_mismatches': mismatches,
              'dependency_import_failures': import_failures,
              'dependency_import_status': 'INCOMPLETE' if import_failures else 'PASS',
              'archives': arrays,
              'scope': 'hashes, syntax, structure and optional dependency imports only'}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
