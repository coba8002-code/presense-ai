"""Offline CLI for a locally trained experimental adapter; no API auto-deployment."""
import argparse
import json
from pathlib import Path

from training.small_vlm import MODEL, REVISION, image_from_bytes, load_base, predict


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, help='Training output directory with report.json and adapter/')
    parser.add_argument('--image', required=True, help='Local PNG/JPEG, no remote URL')
    parser.add_argument('--allow-synthetic', action='store_true', help='Explicitly allow smoke-only adapter for debugging')
    args = parser.parse_args()
    root = Path(args.run)
    report = json.loads((root / 'report.json').read_text())
    config = json.loads((root / 'adapter' / 'adapter_config.json').read_text())
    if (report.get('model') != MODEL or report.get('revision') != REVISION
            or config.get('base_model_name_or_path') != MODEL
            or config.get('peft_type') != 'LORA'):
        raise ValueError('Adapter is not for the pinned base model')
    if report.get('synthetic') is not False and not args.allow_synthetic:
        raise ValueError('Synthetic/unverified adapter requires explicit debugging flag')
    path = Path(args.image)
    if not path.is_file() or not 0 < path.stat().st_size <= 8 * 1024 * 1024:
        raise ValueError('Expected bounded local image')
    image = image_from_bytes(path.read_bytes())
    from peft import PeftModel
    processor, base = load_base()
    if not (root / 'adapter' / 'adapter_model.safetensors').is_file():
        raise ValueError('Safetensors adapter required')
    model = PeftModel.from_pretrained(base, root / 'adapter', use_safetensors=True)
    label = predict(processor, model, image)
    print(json.dumps(dict(posture=label, abstained=label == 'unknown',
                         production_ready=False, synthetic=report['synthetic'],
                         note='Experimental single-frame output; non-dog rejection accuracy unvalidated')))


if __name__ == '__main__':
    main()
