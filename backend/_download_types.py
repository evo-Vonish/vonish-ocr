import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

from pathlib import Path
from huggingface_hub import hf_hub_download
import json
import shutil

BASE_DIR = Path("F:/VonishOCR/test_images")
repo = "opendatalab/OmniDocBench"
full_img_dir = "images"
full_dir = BASE_DIR / "omnidocbench_full"
json_path = full_dir / "OmniDocBench.json"

with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total dataset: {len(data)} pages")

def dl(img_name, dest_dir):
    try:
        if (full_dir / img_name).exists():
            shutil.copy2(str(full_dir / img_name), str(dest_dir / img_name))
            return True, (dest_dir / img_name).stat().st_size
        path = hf_hub_download(
            repo_id=repo, filename=img_name, subfolder=full_img_dir,
            local_dir=str(dest_dir), local_dir_use_symlinks=False, repo_type="dataset",
        )
        return True, Path(path).stat().st_size
    except Exception as e:
        return False, 0

# ── 1. Exam Papers (试卷) ──────────────────────────────
print("\n" + "="*50)
print("[1/6] Exam Papers (试卷)")
print("="*50)

exam_items = [item for item in data if item['page_info']['page_attribute'].get('data_source') == 'exam']
dest = BASE_DIR / "exam_papers"
dest.mkdir(parents=True, exist_ok=True)

count, size = 0, 0
for item in exam_items:
    img = Path(item['page_info']['image_path']).name
    ok, sz = dl(img, dest)
    if ok:
        count += 1
        size += sz
print(f"  Downloaded: {count} images | {size/1024/1024:.1f} MB")

# ── 2. Handwritten Notes (手写笔记) ────────────────────
print("\n" + "="*50)
print("[2/6] Handwritten Notes (手写笔记)")
print("="*50)

note_items = [item for item in data 
              if item['page_info']['page_attribute'].get('data_source') == 'note'
              or 'handwriting' in item['page_info']['page_attribute'].get('special_issue', [])]
dest = BASE_DIR / "handwritten_notes"
dest.mkdir(parents=True, exist_ok=True)

count, size = 0, 0
for item in note_items:
    img = Path(item['page_info']['image_path']).name
    ok, sz = dl(img, dest)
    if ok:
        count += 1
        size += sz
print(f"  Downloaded: {count} images | {size/1024/1024:.1f} MB")

# ── 3. Academic Literature (学术论文, 含公式) ─────────
print("\n" + "="*50)
print("[3/6] Academic Literature (学术论文, 公式)")
print("="*50)

academic_items = [item for item in data if item['page_info']['page_attribute'].get('data_source') == 'academic_literature']
dest = BASE_DIR / "academic_papers"
dest.mkdir(parents=True, exist_ok=True)

count, size = 0, 0
for item in academic_items:
    img = Path(item['page_info']['image_path']).name
    ok, sz = dl(img, dest)
    if ok:
        count += 1
        size += sz
print(f"  Downloaded: {count} images | {size/1024/1024:.1f} MB")

# ── 4. Textbooks (教材, 中英混排+公式) ────────────────
print("\n" + "="*50)
print("[4/6] Textbooks (教材)")
print("="*50)

textbook_items = [item for item in data if 'jiaocai' in item['page_info']['image_path']]
dest = BASE_DIR / "textbooks"
dest.mkdir(parents=True, exist_ok=True)

count, size = 0, 0
for item in textbook_items[:25]:
    img = Path(item['page_info']['image_path']).name
    ok, sz = dl(img, dest)
    if ok:
        count += 1
        size += sz
print(f"  Downloaded: {count} images | {size/1024/1024:.1f} MB")

# ── 5. Newspapers (报纸, 中文密集排版) ────────────────
print("\n" + "="*50)
print("[5/6] Newspapers (报纸)")
print("="*50)

news_items = [item for item in data if 'newspaper' in item['page_info']['image_path']]
dest = BASE_DIR / "newspapers"
dest.mkdir(parents=True, exist_ok=True)

count, size = 0, 0
for item in news_items[:20]:
    img = Path(item['page_info']['image_path']).name
    ok, sz = dl(img, dest)
    if ok:
        count += 1
        size += sz
print(f"  Downloaded: {count} images | {size/1024/1024:.1f} MB")

# ── 6. Research Reports (研报, 表格+混排) ──────────────
print("\n" + "="*50)
print("[6/6] Research Reports (研报)")
print("="*50)

report_items = [item for item in data if 'yanbao' in item['page_info']['image_path']]
dest = BASE_DIR / "research_reports"
dest.mkdir(parents=True, exist_ok=True)

count, size = 0, 0
for item in report_items[:20]:
    img = Path(item['page_info']['image_path']).name
    ok, sz = dl(img, dest)
    if ok:
        count += 1
        size += sz
print(f"  Downloaded: {count} images | {size/1024/1024:.1f} MB")

# ── Summary ────────────────────────────────────────────
print("\n" + "="*50)
print("DOWNLOAD SUMMARY")
print("="*50)

total_files = 0
total_bytes = 0
for subdir in sorted(BASE_DIR.iterdir()):
    if subdir.is_dir():
        imgs = [f for f in subdir.rglob("*") if f.is_file() and f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.bmp', '.webp')]
        sz = sum(f.stat().st_size for f in imgs)
        total_files += len(imgs)
        total_bytes += sz
        print(f"  [{subdir.name:22s}] {len(imgs):3d} images | {sz/1024/1024:6.1f} MB")

print(f"\n  TOTAL: {total_files} images | {total_bytes/1024/1024:.1f} MB")
print(f"  Location: {BASE_DIR}")
