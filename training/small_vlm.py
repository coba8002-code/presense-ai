"""Optional SmolVLM2 LoRA experiment; never automatically deployed by the API."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import time

from training.data import approve_dataset, fingerprint

MODEL = 'HuggingFaceTB/SmolVLM2-256M-Video-Instruct'
REVISION = '067788b187b95ebe7b2e040b3e4299e342e5b8fd'
LABELS = ('standing', 'sitting', 'lying', 'unknown')
PROMPT = ('Classify the visible posture of exactly one dog. Reply with exactly one word: '
          'standing, sitting, lying, or unknown. Use unknown for no dog, multiple dogs, '
          'occlusion, uncertainty or any other posture. Do not infer emotions or motion.')


def normalize_prediction(answer):
    answer = answer.strip()
    return answer if answer in LABELS else 'unknown'


def frame_bytes(root, row):
    raw = Path(row['path'])
    path = (root / raw).resolve()
    if raw.is_absolute() or not path.is_relative_to(root) or path.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
        raise ValueError('Expected contained local PNG/JPEG frame')
    if not path.is_file() or not 0 < path.stat().st_size <= 8 * 1024 * 1024:
        raise ValueError('Missing or oversized frame')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != row['sha256']:
        raise ValueError('Frame hash mismatch')
    return data


def load_manifest(manifest, registry):
    manifest = Path(manifest)
    if manifest.stat().st_size > 8 * 1024 * 1024:
        raise ValueError('Manifest too large')
    rows = json.loads(manifest.read_text())
    if not isinstance(rows, list) or not 1 <= len(rows) <= 10000:
        raise ValueError('Expected 1–10000 reviewed frames')
    fields = ('path', 'sha256', 'species', 'label', 'animal_id', 'recording_group',
              'source_id', 'dataset', 'reviewer', 'review_evidence', 'reviewed_at', 'split')
    memberships, hashes, policies = {}, set(), {}
    for row in rows:
        if not isinstance(row, dict) or any(not isinstance(row.get(f), str) or not row[f].strip()
                or row[f] != row[f].strip() for f in fields):
            raise ValueError('Missing or noncanonical reviewed manifest field')
        if row['species'] != 'dog' or row['label'] not in LABELS or row['split'] not in ('train', 'validation', 'test'):
            raise ValueError('Dog-only static posture manifest required')
        policies[row['dataset']] = approve_dataset(registry, row['dataset'])
        for field in ('animal_id', 'recording_group', 'source_id'):
            if row[field].lower() in ('unknown', 'none', 'null', 'pending'):
                raise ValueError('Known grouping identities required')
            key = (field, row[field])
            if key in memberships and memberships[key] != row['split']:
                raise ValueError('Animal/session/source leaks across partitions')
            memberships[key] = row['split']
        frame_bytes(manifest.parent.resolve(), row)
        if row['sha256'] in hashes:
            raise ValueError('Duplicate frame')
        hashes.add(row['sha256'])
    labels = {r['label'] for r in rows}
    if len({r['animal_id'] for r in rows}) < 5 or len(labels) < 2 or any(
            {r['label'] for r in rows if r['split'] == split} != labels
            for split in ('train', 'validation', 'test')):
        raise ValueError('Need five animals and all labels in each partition')
    return rows, policies


def image_from_bytes(data):
    from PIL import Image
    with Image.open(io.BytesIO(data)) as img:
        if img.format not in ('PNG', 'JPEG') or img.width * img.height > 4_000_000 or getattr(img, 'n_frames', 1) != 1:
            raise ValueError('Unsupported frame dimensions/format')
        return img.convert('RGB')


def load_base():
    import torch
    from transformers import AutoProcessor, AutoModelForImageTextToText
    processor = AutoProcessor.from_pretrained(MODEL, revision=REVISION, trust_remote_code=False)
    processor.image_processor.do_image_splitting = False
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL, revision=REVISION, trust_remote_code=False, use_safetensors=True,
        torch_dtype=torch.float32, attn_implementation='eager')
    model.config.use_cache = False
    return processor, model


def batch(processor, image, label=None):
    messages = [{'role': 'user', 'content': [{'type': 'image'}, {'type': 'text', 'text': PROMPT}]}]
    prefix = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    prefix_batch = processor(text=prefix, images=[image], return_tensors='pt')
    if label is None:
        return prefix_batch
    messages.append({'role': 'assistant', 'content': [{'type': 'text', 'text': label}]})
    full = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    result = processor(text=full, images=[image], return_tensors='pt')
    n = prefix_batch['input_ids'].shape[1]
    if not result['input_ids'][0, :n].equal(prefix_batch['input_ids'][0]):
        raise ValueError('Chat template prefix is not aligned; refuse incorrect loss masking')
    result['labels'] = result['input_ids'].clone()
    result['labels'][:, :n] = -100
    if not (result['labels'] != -100).any():
        raise ValueError('No answer tokens')
    return result


def predict(processor, model, image):
    import torch
    model.eval()
    inputs = batch(processor, image).to(model.device)
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=8, do_sample=False)
    return normalize_prediction(processor.decode(output[0, inputs['input_ids'].shape[1]:], skip_special_tokens=True))


def metrics(truth, predicted):
    matrix = [[0 for _ in LABELS] for _ in LABELS]
    for actual, pred in zip(truth, predicted):
        matrix[LABELS.index(actual)][LABELS.index(pred)] += 1
    f1 = []
    for i in range(len(LABELS)):
        support, count = sum(matrix[i]), sum(row[i] for row in matrix)
        if support:
            f1.append(2 * matrix[i][i] / (support + count))
    accepted = [(a, p) for a, p in zip(truth, predicted) if p != 'unknown']
    return dict(samples=len(truth), accuracy=sum(a == p for a, p in zip(truth, predicted))/len(truth),
                macro_f1=sum(f1)/len(f1), labels=LABELS, confusion_matrix=matrix,
                coverage=len(accepted)/len(truth), selective_accuracy=(sum(a == p for a,p in accepted)/len(accepted) if accepted else None),
                calibration=None, calibration_note='No calibrated probability output; production gate remains blocked')


def run(args):
    # Validate all policy/media boundaries before downloading model or importing ML stack.
    rows, policies, root = [], {}, None
    if args.smoke:
        if args.manifest or args.registry:
            raise ValueError('Smoke cannot bypass real-data policy')
        if args.steps > 2:
            raise ValueError('Synthetic smoke capped at two steps')
    else:
        if not args.manifest or not args.registry:
            raise ValueError('Real training requires manifest and registry')
        rows, policies = load_manifest(args.manifest, args.registry)
        root = Path(args.manifest).parent.resolve()
    out = Path(args.output)
    if out.exists():
        raise ValueError('Output directory must be new')
    import torch
    from PIL import Image
    from peft import LoraConfig, PeftModel, get_peft_model
    torch.manual_seed(42)
    torch.set_num_threads(2)
    processor, base = load_base()
    targets = [name for name, _ in base.named_modules()
               if 'text_model' in name and name.endswith(('.q_proj', '.v_proj'))]
    if not targets:
        raise ValueError('No language attention modules found')
    model = get_peft_model(base, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0,
                                          target_modules=targets, bias='none'))
    trainable = {name: p for name, p in model.named_parameters() if p.requires_grad}
    before = {name: p.detach().clone() for name, p in trainable.items()}
    optimizer = torch.optim.AdamW(trainable.values(), lr=1e-4)
    synthetic = Image.new('RGB', (128, 128), (60, 80, 100)) if args.smoke else None
    train = [r for r in rows if r['split'] == 'train']
    report = dict(model=MODEL, revision=REVISION, synthetic=args.smoke or any(p.get('synthetic') for p in policies.values()),
                  production_ready=False, seed=42, lora_rank=8, lora_alpha=16, learning_rate=1e-4,
                  trainable_parameters=sum(p.numel() for p in trainable.values()),
                  dataset_fingerprint=fingerprint(rows), policies=policies, losses=[],
                  frame_scope='single-image posture only; no temporal behavior', evaluations={})
    def evaluate(split):
        part = [r for r in rows if r['split'] == split]
        return metrics([r['label'] for r in part], [predict(processor, model, image_from_bytes(frame_bytes(root,r))) for r in part])
    if not args.smoke:
        # Only validation is inspected before tuning; no test-driven parameter selection.
        report['evaluations']['baseline_validation'] = evaluate('validation')
    started = time.monotonic()
    for step in range(args.steps):
        row = train[step % len(train)] if train else None
        img = synthetic if args.smoke else image_from_bytes(frame_bytes(root, row))
        inputs = batch(processor, img, 'unknown' if args.smoke else row['label'])
        model.train()
        optimizer.zero_grad(set_to_none=True)
        loss = model(**inputs).loss
        if not torch.isfinite(loss):
            raise ValueError('Nonfinite training loss')
        loss.backward()
        torch.nn.utils.clip_grad_norm_(trainable.values(), 1.0)
        optimizer.step()
        report['losses'].append(float(loss.detach()))
    report['optimizer_seconds'] = time.monotonic() - started
    report['adapter_changed'] = any(not p.detach().equal(before[name]) for name,p in trainable.items())
    if not report['adapter_changed']:
        raise ValueError('Optimizer did not change adapter weights')
    if not args.smoke:
        report['evaluations']['tuned_validation'] = evaluate('validation')
        report['evaluations']['tuned_test'] = evaluate('test')
        with model.disable_adapter():
            report['evaluations']['baseline_test'] = evaluate('test')
        fresh_rows, fresh_policies = load_manifest(args.manifest, args.registry)
        if fresh_rows != rows or fresh_policies != policies:
            raise ValueError('Training data/policy changed during execution')
    out.mkdir(parents=True, exist_ok=False)
    model.save_pretrained(out / 'adapter', safe_serialization=True)
    # Reload into the SAME unloaded base; verify all adapter tensors survive serialization.
    unloaded = model.unload()
    reloaded = PeftModel.from_pretrained(unloaded, out / 'adapter', is_trainable=True)
    reloaded_params = dict(reloaded.named_parameters())
    report['adapter_reload_equal'] = all(torch.equal(p.detach(), reloaded_params[name].detach()) for name,p in trainable.items())
    if not report['adapter_reload_equal']:
        raise ValueError('Adapter reload changed weights')
    if args.smoke:
        report['smoke_prediction'] = predict(processor, reloaded, synthetic)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--manifest')
    parser.add_argument('--registry')
    parser.add_argument('--output', required=True)
    parser.add_argument('--steps', type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.steps <= 10000:
        parser.error('steps must be between 1 and 10000')
    run(args)


if __name__ == '__main__':
    main()
